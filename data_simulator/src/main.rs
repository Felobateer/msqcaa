use log::{info, error};
use rdkafka::config::ClientConfig;
use rdkafka::consumer::{Consumer, StreamConsumer};

mod db;
mod app;
mod utils; // Changed to match your file structure

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    dotenvy::dotenv().ok();
    env_logger::init();

    info!("Init data simulator");
    
    // 1. Setup Data Infrastructure
    let pool = db::connect::init_pool().await?;

    info!("Init DB pool Successful");

    db::connect::create_db_tables(&pool).await?;

    let brokers = std::env::var("KAFKA_BROKERS").unwrap_or_else(|_| "localhost:9092".to_string());
    let topic = "ms_data_stream";

    let producer = app::kafka::init_producer(&brokers)?;

    info!("Init Kafka data stream");

    let consumer: StreamConsumer = ClientConfig::new()
        .set("bootstrap.servers", &brokers)
        .set("group.id", "pipeline_group")
        .set("fetch.message.max.bytes", "524288000")
        .set("receive.message.max.bytes", "524288000")
        .set("auto.offset.reset", "earliest")
        .create()?;
    
    consumer.subscribe(&[topic])?;

    // 2. Spawn the consumer daemon
    // We clone the pool so the background thread has its own connection manager
    let consumer_pool = pool.clone(); 
    tokio::spawn(async move {
        info!("Starting Kafka consumer daemon...");
        app::kafka::consume_and_batch(consumer, consumer_pool).await;
    });

    let enable_generator = std::env::var("ENABLE_GENERATOR").unwrap_or_else(|_| "false".to_string());

    if enable_generator == "true" {
        info!("Generator is on");

        let mut interval = tokio::time::interval(std::time::Duration::from_secs(120));

        loop {
            interval.tick().await;

            // 3. Generate Simulation Data
            let (sample, fab_data, centroided_peaks, raw_data) = app::simulator::simulate_paracetamol_run();
    
            // 4. Build all 4 JSON payloads instantly
            let payloads = utils::jsonify::prepare_payloads(&sample, &fab_data, &centroided_peaks, &raw_data)?;
            let key = sample.id.to_string();
    
            // 5. Send to Kafka
            for payload_bytes in payloads {
                app::kafka::write_message(&producer, topic, &key, &payload_bytes).await?;
            }
        }
    } else {
        info!("Generator is off");

        loop {
            tokio::time::sleep(std::time::Duration::from_secs(3600)).await;
        }
    }
}