use log::{info, error};
use rdkafka::{
    config::ClientConfig, 
    consumer::StreamConsumer, 
    producer::{FutureProducer, FutureRecord}, 
    Message
};
use tokio::time::{self, Duration, MissedTickBehavior};
use sqlx::PgPool;
use crate::db::db_functions::flush_to_db;


// 500 MB in bytes
const MAX_MSG_BYTES: &str = "524288000";
const ONE_MB: usize = 1_048_576;

// 1. Create a function to initialize the producer ONCE
pub fn init_producer(brokers: &str) -> Result<FutureProducer, rdkafka::error::KafkaError> {
    ClientConfig::new()
        .set("bootstrap.servers", brokers)
        .set("message.max.bytes", MAX_MSG_BYTES)
        .set("receive.message.max.bytes", MAX_MSG_BYTES)
        .create()
}

// 2. Pass the created producer by reference
pub async fn write_message(
    producer: &FutureProducer, 
    topic: &str, 
    key: &str, 
    payload: &[u8]
) -> Result<(), rdkafka::error::KafkaError> {
    info!("Adding data for topic {} on key {}", topic, key);

    let record = FutureRecord::to(topic).key(key).payload(payload);

    match producer.send(record, Duration::from_secs(5)).await {
        Ok(delivery) => {
            info!("Message sent to partition {} at offset {}", delivery.partition, delivery.offset);
            Ok(())
        }
        Err((e, _)) => {
            error!("Failed to send message: {}", e);
            Err(e)
        }
    }
}


