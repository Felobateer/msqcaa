use serde_json::{json, Value};
use crate::app::simulator::{Sample, FabData, MsData, RawData};

pub fn prepare_payloads(
    sample: &Sample,
    fab_data: &FabData,
    centroided_peaks: &[MsData],
    raw_data: &[RawData],
) -> Result<Vec<Vec<u8>>, serde_json::Error> {
    let mut payloads = Vec::new();

    // Helper closure to quickly format and serialize
    let mut add_payload = |table: &str, data: Value| -> Result<(), serde_json::Error> {
        let payload = json!({
            "table": table,
            "batch_size": "1MB",
            "data": data
        });
        payloads.push(serde_json::to_vec(&payload)?);
        Ok(())
    };

    // jsonb_to_recordset REQUIRES arrays. We must wrap the single structs in json!([...])
    add_payload("samples", json!([sample]))?;
    add_payload("fab_data", json!([fab_data]))?;
    add_payload("ms_data", json!(centroided_peaks))?; // This is already a Vec, no brackets needed
    add_payload("raw_data", json!(raw_data))?;

    Ok(payloads)
}