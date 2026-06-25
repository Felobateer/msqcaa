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


pub async fn consume_and_batch(consumer: StreamConsumer, pool: PgPool) {
    let mut interval = time::interval(Duration::from_secs(5)); // Down to 5 seconds
    interval.set_missed_tick_behavior(MissedTickBehavior::Skip);

    let mut batch: Vec<String> = Vec::new();
    let mut current_batch_size = 0;

    loop {
        tokio::select! {
            _ = interval.tick() => {
                if !batch.is_empty() {
                    info!("Timer expired. Flushing {} records", batch.len());
                    // Catch and log the error instead of crashing
                    if let Err(e) = flush_to_db(&pool, &batch).await {
                        error!("Database insert failed: {}", e);
                    }
                    batch.clear();
                    current_batch_size = 0;
                }
            }

            msg_result = consumer.recv() => {
                match msg_result {
                    Ok(m) => {
                        if let Some(payload) = m.payload() {
                            let msg_size = payload.len();
                            let msg_str = String::from_utf8_lossy(payload).to_string();

                            batch.push(msg_str);
                            current_batch_size += msg_size;

                            if current_batch_size >= ONE_MB {
                                info!("1MB limit reached. Flushing {} records.", batch.len());
                                if let Err(e) = flush_to_db(&pool, &batch).await {
                                    error!("Database insert failed: {}", e);
                                }
                                batch.clear();
                                current_batch_size = 0;
                                interval.reset();
                            }
                        }
                    },
                    Err(e) => error!("Kafka error: {e}"),
                }
            }
        }
    }
}