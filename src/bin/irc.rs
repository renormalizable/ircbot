use futures::prelude::*;
use irc::client::prelude::*;
use tracing::*;
use tracing_subscriber::prelude::*;

use ircbot::{
    base::{BoxCommandObject, Interpreter},
    client::irc::MessageContext,
    command::{api, input, language, music, random, scheme, utility, Config as CommandConfig},
};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .finish()
        .with(tracing_subscriber::filter::Targets::default().with_default(Level::INFO))
        .init();

    let irc = {
        let prefix = format!("{}/data/irc", env!("CARGO_MANIFEST_DIR"));
        let file = Config::load(format!("{}/irc.yaml", prefix))?;

        Config {
            cert_path: file.cert_path().map(|p| format!("{}/{}", prefix, p)),
            client_cert_path: file.client_cert_path().map(|p| format!("{}/{}", prefix, p)),
            ..file
        }
    };

    let config = {
        let prefix = format!("{}/data", env!("CARGO_MANIFEST_DIR"));
        let file = CommandConfig::load(format!("{}/config.yaml", prefix))?;

        file
    };

    let command: Vec<BoxCommandObject> = vec![
        Box::new(input::Kana),
        Box::new(input::Romaji),
        Box::new(input::Bim),
        Box::new(input::Gim),
        Box::new(utility::Echo),
        Box::new(utility::Lower),
        Box::new(utility::Upper),
        Box::new(utility::Utc),
        Box::new(scheme::Newline),
        Box::new(scheme::Include),
        Box::new(scheme::Display),
        Box::new(language::Wandbox),
        Box::new(language::Geordi),
        Box::new(language::Rust),
        Box::new(language::Go),
        Box::new(language::ReplPython),
        Box::new(language::ReplRust),
        Box::new(random::Leetcode),
        Box::new(api::Urban),
        Box::new(api::Ipapi),
        Box::new(api::Poke),
        Box::new(api::CratesIo),
        Box::new(api::Wolfram::new(&config.command.wolfram)),
        Box::new(api::Google::new(&config.command.google)),
        Box::new(api::Btran::new(&config.command.baidu_translate)),
        Box::new(api::Gtran::new(&config.command.google_translate)),
        Box::new(api::Bangumi),
        Box::new(api::Speedrun),
        Box::new(api::Movie),
        Box::new(music::Music),
        Box::new(music::Music163),
        Box::new(music::MusicQQ),
    ];

    let bot = Interpreter::new(command);

    let mut client = Client::from_config(irc).await?;
    client.identify()?;

    let stream = client.stream()?;

    stream
        .try_filter_map(|message| async move {
            Ok(match message {
                irc::client::prelude::Message {
                    tags: _,
                    prefix: Some(Prefix::Nickname(source, _, _)),
                    command: Command::PRIVMSG(target, message),
                } => Some((source, target, message)),
                _ => None,
            })
        })
        .try_for_each_concurrent(None, |(source, target, message)| async {
            info!("[{target}] <{source}> {message:?}");

            let context = MessageContext::new(
                client.current_nickname().to_owned(),
                source,
                target,
                message,
                client.sender(),
            );

            if let Some(text) = context.message().strip_prefix("'") {
                bot.evaluate(&context, text).await
            }

            Ok(())
        })
        .await?;

    Ok(())
}
