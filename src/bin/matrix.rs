use anyhow::Context as _;
use futures::prelude::*;
use matrix_sdk::{
    config,
    room::Room,
    ruma::{
        events::{
            relation::{InReplyTo, Replacement},
            room::message::{Relation, SyncRoomMessageEvent},
            AnyTimelineEvent,
        },
        UserId,
    },
    Client, RoomMemberships, RoomState,
};
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, fs::File, io::Read, path::Path, sync::Arc, thread, time};
use tracing::*;
use tracing_subscriber::prelude::*;

use ircbot::{
    base::{BoxCommandObject, CommandObject, Context as _, Interpreter},
    client::matrix::MessageContext,
    command::{api, input, language, music, random, scheme, utility, Config as CommandConfig},
};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::from_default_env())
        .with(tracing_subscriber::fmt::layer())
        .init();

    let matrix = {
        let prefix = format!("{}/data/matrix", env!("CARGO_MANIFEST_DIR"));
        let file = Config::load(format!("{}/matrix.yaml", prefix))?;

        Config {
            store_path: Some(prefix),
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
        Box::new(api::Room),
        Box::new(music::Music),
        Box::new(music::Music163),
        Box::new(music::MusicQQ),
    ];

    let command_test: Vec<BoxCommandObject> = vec![
        Box::new(input::Kana),
        Box::new(input::Romaji),
        Box::new(input::Bim),
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
        Box::new(api::Btran::new(&config.command.baidu_translate)),
        Box::new(api::Bangumi),
        Box::new(api::Speedrun),
        Box::new(api::Movie),
        Box::new(api::Room),
        Box::new(music::Music),
        Box::new(music::Music163),
        Box::new(music::MusicQQ),
    ];

    let interpreter = {
        let mut map = HashMap::new();

        map.insert("disable".to_string(), Interpreter::new(Vec::new()));
        map.insert("default".to_string(), Interpreter::new(command));
        map.insert("test_matrix".to_string(), Interpreter::new(command_test));

        Arc::new(map)
    };

    let router = Arc::new(
        config
            .router
            .raw
            .get("matrix")
            .context("router error")?
            .iter()
            .map(|(source, target, key)| -> anyhow::Result<_> {
                Ok((
                    Regex::new(source).context("regex error")?,
                    Regex::new(target).context("regex error")?,
                    key.clone(),
                ))
            })
            .collect::<Result<Vec<_>, _>>()?,
    );

    loop {
        match client(&matrix, Arc::clone(&interpreter), Arc::clone(&router)).await {
            Ok(_) => break,
            Err(err) => {
                warn!("reconnect: {err:?}");
                thread::sleep(time::Duration::from_secs(10));
            }
        }
    }

    Ok(())
}

async fn client<T>(
    matrix: &Config,
    interpreter: Arc<HashMap<String, Interpreter<T>>>,
    router: Arc<Vec<(Regex, Regex, String)>>,
) -> anyhow::Result<()>
where
    T: CommandObject + Send + 'static,
{
    let user = UserId::parse(&matrix.user_id)?;

    let client = Client::builder()
        .server_name(&user.server_name())
        //.sqlite_store(matrix.store_path.clone().unwrap(), None)
        .build()
        .await?;

    client
        .matrix_auth()
        .login_username(&user, &matrix.password)
        .send()
        .await?;

    // discard old events
    let response = client.sync_once(config::SyncSettings::default()).await?;
    client.add_event_handler(
        move |event: SyncRoomMessageEvent, room: Room, client: Client| {
            let interpreter = Arc::clone(&interpreter);
            let router = Arc::clone(&router);

            async move {
                match room.state() {
                    RoomState::Joined => (),
                    _ => return,
                }
                let event = match event {
                    SyncRoomMessageEvent::Original(event) => event,
                    _ => {
                        info!(
                            "[{}{}] {event:?}",
                            room.room_id(),
                            room.name()
                                .map_or_else(|| String::new(), |x| format!(" / {x}")),
                        );
                        return;
                    }
                };
                let member = match room.get_member_no_sync(&event.sender).await {
                    Ok(Some(member)) => member,
                    _ => return,
                };
                let members = match room.members_no_sync(RoomMemberships::JOIN).await {
                    Ok(members) => members,
                    _ => return,
                };

                info!(
                    "[{}{}] <{}> {event:?}",
                    room.room_id(),
                    room.name()
                        .map_or_else(|| String::new(), |x| format!(" / {x}")),
                    member.name()
                );

                let event = event.into_full_event(room.room_id().to_owned());
                let reply = match &event.content.relates_to {
                    Some(
                        Relation::Reply {
                            in_reply_to: InReplyTo { event_id, .. },
                        }
                        | Relation::Replacement(Replacement { event_id, .. }),
                    ) => room.event(&event_id).await.ok().and_then(|event| {
                        match event.event.deserialize() {
                            Ok(AnyTimelineEvent::MessageLike(message)) => Some(message),
                            _ => None,
                        }
                    }),
                    _ => None,
                };

                stream::iter(MessageContext::new(event, reply, members, room, client))
                    .for_each(|context| {
                        let interpreter = Arc::clone(&interpreter);
                        let router = Arc::clone(&router);

                        async move {
                            if let Some(text) = context.message().strip_prefix("'") {
                                for (source, target, key) in router.iter() {
                                    if source.is_match(context.source())
                                        && target.is_match(context.target())
                                    {
                                        if let Some(int) = interpreter.get(key.as_str()) {
                                            int.evaluate(&context, text).await;
                                            break;
                                        }
                                    }
                                }
                            }
                        }
                    })
                    .await
            }
        },
    );
    client
        .sync(config::SyncSettings::default().token(response.next_batch))
        .await?;

    Ok(())
}

#[derive(Deserialize, Serialize)]
struct Config {
    user_id: String,
    password: String,
    store_path: Option<String>,
}

impl Config {
    fn load<P>(path: P) -> anyhow::Result<Self>
    where
        P: AsRef<Path>,
    {
        let mut file = File::open(path)?;
        let mut data = String::new();
        file.read_to_string(&mut data)?;

        Ok(serde_yaml::from_str(&data).context("config error")?)
    }
}
