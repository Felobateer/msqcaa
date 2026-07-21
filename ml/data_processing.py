from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, DoubleType, IntegerType

# 1. Initialize Spark with Kafka dependencies
spark = SparkSession.builder \
    .appName("FabDataStreaming") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

# 2. Define the schema that matches the JSON produced by your Rust app
schema = StructType([
    StructField("sample_id", IntegerType(), True),
    StructField("temperature", DoubleType(), True),
    StructField("pressure", DoubleType(), True),
    StructField("ph_level", DoubleType(), True)
])

# 3. Read the stream from Kafka
kafka_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "fab_data_stream") \
    .option("startingOffsets", "earliest") \
    .load()

# 4. Parse the JSON data
parsed_stream = kafka_stream.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

# Define the batch writing logic
def write_to_postgres(batch_df, batch_id):
    batch_df.write \
        .format("jdbc") \
        .option("url", "jdbc:postgresql://db:5432/your_db_name") \
        .option("dbtable", "your_table_name") \
        .option("user", "your_user") \
        .option("password", "your_password") \
        .option("driver", "org.postgresql.Driver") \
        .mode("append") \
        .save()

# 5. Process and output the micro-batches to PostgreSQL
query = parsed_stream.writeStream \
    .foreachBatch(write_to_postgres) \
    .start()

query.awaitTermination()