use anyhow::Context as _;
use futures::prelude::*;
use matrix_sdk::{
    config,
    room::Room,
    ruma::{
        events::{
            room::message::{InReplyTo, Relation, Replacement, SyncRoomMessageEvent},
            AnyTimelineEvent,
        },
        UserId,
    },
    store, Client,
};
use serde::{Deserialize, Serialize};
use std::{fs::File, io::Read, path::Path, sync::Arc};
use tracing::*;
use tracing_subscriber::prelude::*;

use ircbot::{
    base::{BoxCommandObject, Interpreter},
    client::matrix::MessageContext,
    command::{api, input, language, music, random, scheme, utility, Config as CommandConfig},
};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .finish()
        .with(
            tracing_subscriber::filter::Targets::default()
                .with_default(Level::INFO)
                .with_target("matrix_sdk_base", Level::WARN)
                .with_target("matrix_sdk_sled", Level::WARN),
        )
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

    let user = UserId::parse(matrix.user_id)?;

    let store = store::make_store_config(matrix.store_path.unwrap(), None)?;

    let client = Client::builder()
        .server_name(&user.server_name())
        .store_config(store)
        .build()
        .await?;

    client
        .login_username(&user, &matrix.password)
        .send()
        .await?;

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

    let bot = Arc::new(Interpreter::new(command));

    client.sync_once(config::SyncSettings::default()).await?;
    client.add_event_handler(
        move |event: SyncRoomMessageEvent, room: Room, client: Client| {
            let bot = Arc::clone(&bot);

            async move {
                let room = match room {
                    Room::Joined(room) => room,
                    _ => return,
                };
                let event = match event {
                    SyncRoomMessageEvent::Original(event) => event,
                    _ => {
                        info!(
                            "[{}{}] {event:?}",
                            room.room_id(),
                            room.name()
                                .map(|x| format!(" / {x}"))
                                .unwrap_or(String::new())
                        );
                        return;
                    }
                };
                let member = match room.get_member_no_sync(&event.sender).await {
                    Ok(Some(member)) => member,
                    _ => return,
                };
                let members = match room.members_no_sync().await {
                    Ok(members) => members,
                    _ => return,
                };

                info!(
                    "[{}{}] <{}> {event:?}",
                    room.room_id(),
                    room.name()
                        .map(|x| format!(" / {x}"))
                        .unwrap_or(String::new()),
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
                        let bot = Arc::clone(&bot);

                        async move {
                            if let Some(text) = context.message().strip_prefix("'") {
                                bot.evaluate(&context, text).await
                            }
                        }
                    })
                    .await
            }
        },
    );
    // NOTE sync_token() should always success as we have already called sync_once() before
    client
        .sync(config::SyncSettings::default().token(client.sync_token().await.unwrap()))
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
