use log::{info, error};
use sqlx::{Error, PgPool, postgres::PgPoolOptions};
use std::env;

pub async fn init_pool() -> Result<PgPool, Box<dyn std::error::Error>> {
    let db_url = env::var("DB_URL").unwrap_or_else(|_| {
        error!("Failed to fetch the database url");
        std::process::exit(1);
    });

    let pool = PgPoolOptions::new()
        .max_connections(5)
        .connect(&db_url)
        .await?;

    info!("DB Connection is Successful");

    Ok(pool)
}


pub async fn create_db_tables(pool: &PgPool) -> Result<(), Error> {

    let table_queries = [
        (
            "samples", 
            "id UUID PRIMARY KEY, number BIGINT, synthesis_date TIMESTAMPTZ, analysis_date TIMESTAMPTZ"
        ),
        (
            "fab_data", 
            "id UUID PRIMARY KEY, sample_id UUID REFERENCES samples(id), timestamp TIMESTAMPTZ, temperature DOUBLE PRECISION, pressure DOUBLE PRECISION, ph_level DOUBLE PRECISION"
        ),
        (
            "ms_data", 
            "id UUID PRIMARY KEY, sample_id UUID REFERENCES samples(id), mass_to_charge DOUBLE PRECISION, charge INT, intensity DOUBLE PRECISION"
        ),
        (
            "raw_data", 
            "id UUID PRIMARY KEY, sample_id UUID REFERENCES samples(id), mz DOUBLE PRECISION, intensity DOUBLE PRECISION"
        )
    ];

    for (table_name, cols) in table_queries {
        // Added parentheses around the columns and fixed the SQL command
        let query = format!("CREATE TABLE IF NOT EXISTS {} ({});", table_name, cols);

        // Pass the query by reference
        sqlx::query(&query)
        .execute(pool)
        .await?;

        info!("Successfully created table: {} with cols: {}", table_name, cols);
    }

    // --- CREATE INDEXES ---
    let index_queries = [
        "CREATE INDEX IF NOT EXISTS idx_fab_sample_id ON fab_data(sample_id);",
        "CREATE INDEX IF NOT EXISTS idx_ms_sample_id ON ms_data(sample_id);",
        "CREATE INDEX IF NOT EXISTS idx_raw_sample_id ON raw_data(sample_id);",
        "CREATE INDEX IF NOT EXISTS idx_samples_number ON samples(number);"
    ];

    for idx_query in index_queries {
        sqlx::query(idx_query).execute(pool).await?;
    }
    
    Ok(())
}

