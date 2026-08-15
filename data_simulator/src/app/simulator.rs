use chrono::Utc;
use log::{error, info};
use ndarray::Array1;
use rand::thread_rng;
use rand_distr::{Distribution, Normal, Uniform};
use serde::Serialize;
use uuid::Uuid;

#[derive(Serialize)]
pub struct Sample {
    pub id: Uuid,
    pub number: i64,
    pub synthesis_date: String,
    pub analysis_date: String,
}

#[derive(Serialize)]
pub struct FabData {
    pub id: Uuid,
    pub sample_id: Uuid,
    pub timestamp: String,
    pub temperature: f64,
    pub pressure: f64,
    pub ph_level: f64,
}

#[derive(Serialize)]
pub struct MsData {
    pub id: Uuid,
    pub sample_id: Uuid,
    pub mass_to_charge: f64,
    pub charge: i32,
    pub intensity: f64,
}

#[derive(Serialize)]
pub struct RawData {
    pub id: Uuid,
    pub sample_id: Uuid,
    pub mz: f64,
    pub intensity: f64,
}

pub fn simulate_paracetamol_run() -> (Sample, FabData, Vec<MsData>, Vec<RawData>) {
    let mut rng = thread_rng();
    let sample_id = Uuid::new_v4();
    let utc_now = Utc::now();
    let now_rfc = utc_now.to_rfc3339();

    // Format strictly as numbers: YYYYMMDDHHMM
    let sample_number_str = utc_now.format("%Y%m%d%H%M").to_string();
    let sample_number: i64 = sample_number_str.parse().unwrap();

    info!("Sample number: {} is now being generated", sample_number);

    let sample = Sample {
        id: sample_id,
        number: sample_number,
        synthesis_date: now_rfc.clone(),
        analysis_date: now_rfc.clone(),
    };

    let fab_data = FabData {
        id: Uuid::new_v4(),
        sample_id,
        timestamp: now_rfc,
        temperature: Normal::new(140.0, 2.5).unwrap().sample(&mut rng),
        pressure: Normal::new(1.0, 0.05).unwrap().sample(&mut rng),
        ph_level: Normal::new(6.0, 0.2).unwrap().sample(&mut rng),
    };

    let mz_axis: Array1<f64> = Array1::linspace(50.0, 200.0, 1500);
    let mut intensity_axis: Array1<f64> = Array1::zeros(1500);

    // Paracetamol actual major peaks
    let target_peaks = vec![
        (152.07, 10000.0), // Parent ion (base peak)
        (110.06, 6000.0),  // Fragment 1
        (65.04, 2500.0),   // Fragment 2
    ];

    let mut centroided_peaks = Vec::new();
    let jitter_dist = Normal::new(0.0, 0.02).unwrap(); // Mass accuracy jitter (+/- 0.02 Da)
    let noise_dist = Uniform::new(50.0, 150.0); // Baseline noise

    for (exact_mz, base_intensity) in target_peaks {
        // Add instrument jitter to the peak location and height
        let observed_mz = exact_mz + jitter_dist.sample(&mut rng);
        let observed_intensity = base_intensity * Normal::new(1.0, 0.1).unwrap().sample(&mut rng);

        // Create the peak shape using a Gaussian function
        let peak_width = 0.1; // peak std
        for i in 0..mz_axis.len() {
            let mz = mz_axis[i];
            let exponent = -((mz - observed_mz).powi(2)) / (2.0 * peak_width * peak_width);
            intensity_axis[i] += observed_intensity * exponent.exp();
        }

        // save to centroided (extracted) data table
        centroided_peaks.push(MsData {
            id: Uuid::new_v4(),
            sample_id,
            mass_to_charge: observed_mz,
            charge: 1,
            intensity: observed_intensity,
        });
    }

    for val in intensity_axis.iter_mut() {
        *val += noise_dist.sample(&mut rng);
    }

    let mut raw_data: Vec<RawData> = Vec::with_capacity(mz_axis.len());

    if mz_axis.len() == intensity_axis.len() {
        for i in 0..mz_axis.len() {
            raw_data.push(RawData {
                // Changed from append to push
                id: Uuid::new_v4(),
                sample_id,
                mz: mz_axis[i],
                intensity: intensity_axis[i],
            });
        }
    } else {
        error!(
            "mismatch length between mz: {} and intensity: {} in raw data",
            mz_axis.len(),
            intensity_axis.len()
        );
    }

    info!(
        "Generating Sample is now sucessful \n sample id: {} \n fab_data id: {} \n centroided length: {} \n raw data length: {}",
        sample.id,
        fab_data.id,
        centroided_peaks.len(),
        raw_data.len()
    );

    (sample, fab_data, centroided_peaks, raw_data)
}
