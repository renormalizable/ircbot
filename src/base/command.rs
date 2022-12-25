use async_trait::async_trait;
use futures::prelude::*;
use pest::{iterators::Pairs, Parser, RuleType};
use pest_derive::Parser;
use std::{borrow::Cow, collections::HashMap, fmt::Debug};
use tracing::*;

use super::{BoxContext, Collector, Context, Error};

#[async_trait]
pub trait Command: CommandParser<Self::Key> {
    // parameter key
    type Key;
    async fn execute(
        // stateful commands should use lock themselves
        &self,
        // NOTE Context needs to be Sized as required by some of the methods
        context: &impl Context,
        parameter: <Self as CommandParser<Self::Key>>::Parameter<'_>,
    ) -> Result<(), Error>;

    fn name(&self) -> Option<&str> {
        None
    }
    fn help(&self) -> Option<&str> {
        None
    }
}

// command parser
pub trait CommandParser<R> {
    type Parameter<'a>: Debug;
    fn parse<'a>(&self, message: &'a str) -> Result<Self::Parameter<'a>, Error>;
}

// pest
impl<T, R> CommandParser<R> for T
where
    T: Parser<R> + Command,
    R: RuleType + Default,
{
    type Parameter<'a> = HashMap<R, &'a str>;

    fn parse<'a>(&self, message: &'a str) -> Result<Self::Parameter<'a>, Error> {
        match <Self as Parser<R>>::parse(R::default(), message) {
            Ok(rules) => Ok(rules.map(|pair| (pair.as_rule(), pair.as_str())).collect()),
            Err(_) => Err(Error::ParseError),
        }
    }
}

#[async_trait]
pub trait CommandObject: Sync {
    //async fn execute(&self, context: &dyn Context, message: &str) -> Result<(), Error>;
    async fn execute(&self, context: &BoxContext, message: &str) -> Result<(), Error>;
    fn name(&self) -> Option<&str>;
    fn help(&self) -> Option<&str>;
}

#[async_trait]
impl<T> CommandObject for T
where
    T: Command + Sync,
{
    //async fn execute(&self, context: &dyn Context, message: &str) -> Result<(), Error> {
    async fn execute(&self, context: &BoxContext, message: &str) -> Result<(), Error> {
        // NOTE combine the future first as the parameter may not be Send
        let future = match <Self as CommandParser<<Self as Command>::Key>>::parse(self, message) {
            Ok(parameter) => {
                info!("execute: {} {parameter:?}", std::any::type_name::<Self>());

                <Self as Command>::execute(self, context, parameter).left_future()
            }
            Err(error) => future::err(error).right_future(),
        };

        future.await
    }
    fn name(&self) -> Option<&str> {
        <Self as Command>::name(self)
    }
    fn help(&self) -> Option<&str> {
        <Self as Command>::help(self)
    }
}

// similar to BoxFuture and LocalBoxFuture
#[allow(dead_code)]
pub type BoxCommandObject<'a> = Box<dyn CommandObject + Send + 'a>;
#[allow(dead_code)]
pub type LocalBoxCommandObject<'a> = Box<dyn CommandObject + 'a>;

#[derive(Debug, Parser)]
#[grammar = "base/command.pest"]
enum Node<'a> {
    Text(&'a str),
    Quotation(&'a str),
    Substitution(Vec<Node<'a>>),
}

impl<'a> Node<'a> {
    pub fn new(message: &'a str) -> Result<Vec<Self>, Error> {
        Self::parse(Rule::input, message)
            .map(|mut rules| Self::descent(rules.next().unwrap().into_inner()))
            .map_err(|_| Error::SubstituteError)
    }

    fn descent(pairs: Pairs<'a, Rule>) -> Vec<Self> {
        pairs
            .map(|pair| match pair.as_rule() {
                Rule::text => Self::Text(pair.as_str()),
                Rule::quot => Self::Quotation(pair.as_str()),
                Rule::subs => Self::Substitution(Self::descent(pair.into_inner())),
                _ => unreachable!(),
            })
            .collect::<Vec<_>>()
    }
}

pub struct Interpreter<'t> {
    commands: Vec<BoxCommandObject<'t>>,
}

impl<'t> Interpreter<'t> {
    pub fn new(commands: Vec<BoxCommandObject<'t>>) -> Self {
        Self { commands }
    }

    pub async fn evaluate(&self, context: &impl Context, message: &str) {
        let _ = self
            .try_evaluate(context, message)
            .or_else(|err| async move {
                warn!("{err:?}");
                match err {
                    Error::NoOutput => context.send_fmt("╮(￣▽￣)╭").await,
                    Error::Message(message) => {
                        context.send_fmt(format!("╮(￣▽￣)╭ {message}")).await
                    }
                    Error::Error(_) => context.send_fmt(format!("╮(￣▽￣)╭")).await,
                    _ => Ok(()),
                }
            })
            .await;
    }

    pub async fn try_evaluate(&self, context: &impl Context, message: &str) -> Result<(), Error> {
        info!("evaluate: {message:?}");

        // NOTE Pairs and Pair contain Rc which forbids using await within match arms
        match Node::new(message) {
            Ok(nodes) => {
                self.command(context, &self.substitute(context, nodes).await?)
                    .await
            }
            Err(_) => self.command(context, message).await,
        }
    }

    // NOTE BoxFuture is required as the depth of the expression is not known to the compiler
    fn substitute<'s, 'a, 'b, 'c>(
        &'s self,
        context: &'a impl Context,
        nodes: Vec<Node<'b>>,
    ) -> future::BoxFuture<'c, Result<String, Error>>
    where
        'a: 'c,
        'b: 'c,
        's: 'c,
        't: 'c,
    {
        debug!("{nodes:?}");

        nodes
            .into_iter()
            .map(|node| async move {
                match node {
                    Node::Text(text) | Node::Quotation(text) => Ok(Cow::Borrowed(text)),
                    Node::Substitution(nodes) => {
                        let text = self.substitute(context, nodes).await?;
                        let (collector, stream) = Collector::new();
                        match {
                            // move the collector into the block so that UnboundedSender will be dropped after command finishes
                            let collector = collector;
                            self.command(&collector, &text).await
                        } {
                            Ok(_) => Ok(Cow::Owned(stream.collect::<Vec<_>>().await.join("\n"))),
                            // ignore parse error
                            Err(Error::ParseError) => Ok(Cow::Owned(format!("({text})"))),
                            // propagate other errors
                            Err(err) => Err(err),
                        }
                    }
                }
            })
            .collect::<stream::FuturesOrdered<_>>()
            .try_collect::<String>()
            .boxed()
    }

    async fn command(&self, context: &impl Context, message: &str) -> Result<(), Error> {
        debug!("{message:?}");

        let box_context: BoxContext = Box::new(context);

        for cmd in &self.commands {
            match cmd
                //.execute(context, message)
                .execute(&box_context, message)
                .await
            {
                Err(Error::ParseError) => (),
                Ok(_) => return Ok(()),
                Err(err) => return Err(err),
            }
        }

        Err(Error::ParseError)
    }
}
