use log::{error, info};
use serde_json::Value;
use sqlx::PgPool;

pub async fn flush_to_db(
    pool: &PgPool,
    batch: &[String],
) -> Result<(), Box<dyn std::error::Error>> {
    info!("Flush to DB. batch size: {}", batch.len());

    for payload_str in batch {
        let parsed: Value = serde_json::from_str(payload_str)?;
        let table_name = parsed["table"].as_str().ok_or("Missing table name")?;

        if !table_name.chars().all(|c| c.is_alphanumeric() || c == '_') {
            return Err("Invalid table name characters".into());
        }

        let data_array = &parsed["data"];

        // Added ::jsonb cast here
        let query = format!(
            "INSERT INTO {0} SELECT * FROM jsonb_populate_recordset(null::{0}, $1::jsonb)",
            table_name
        );
        info!(
            "INSERT INTO {0} SELECT * FROM jsonb_populate_recordset(null::{0}, $1::jsonb)",
            table_name
        );

        sqlx::query(&query).bind(data_array).execute(pool).await?;
    }
    Ok(())
}
