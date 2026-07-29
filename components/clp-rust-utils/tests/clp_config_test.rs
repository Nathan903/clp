use clp_rust_utils::{
    clp_config::{AwsAuthentication, AwsCredentials, S3Config},
    job_config::{
        ClpIoConfig,
        ClpSOutputConfig,
        InputConfig,
        OutputConfig,
        S3ObjectMetadataInputConfig,
    },
    serde::BrotliMsgpack,
    types::non_empty_string::ExpectedNonEmpty,
};
use non_empty_string::NonEmptyString;
use serde_json::Value;

#[test]
fn test_clp_io_config_serialization() {
    let s3_config = S3Config {
        bucket: NonEmptyString::from_static_str("yscope"),
        region_code: Some(NonEmptyString::from_static_str("us-east-2")),
        key_prefix: NonEmptyString::from_static_str("sample-logs/cockroachdb.clp.zst"),
        endpoint_url: None,
        aws_authentication: AwsAuthentication::Credentials {
            credentials: AwsCredentials {
                access_key_id: "ACCESS_KEY_ID".into(),
                secret_access_key: "SECRET_ACCESS_KEY".into(),
            },
        },
    };
    let config = ClpIoConfig {
        input: InputConfig::S3ObjectMetadataInputConfig {
            config: S3ObjectMetadataInputConfig {
                s3_config,
                ingestion_job_id: 1,
                s3_object_metadata_ids: vec![],
                dataset: Some(NonEmptyString::from_static_str("test-dataset")),
                timestamp_key: Some(NonEmptyString::from_static_str("timestamp")),
                unstructured: false,
            },
        },
        output: OutputConfig {
            compression_level: 3,
            target_uncompressed_size: 268_435_456,
            clp_s: ClpSOutputConfig {
                target_encoded_size: 301_989_888,
            },
        },
    };

    let brotli_compressed_msgpack = BrotliMsgpack::serialize(&config)
        .expect("Brotli-compressed MessagePack serialized config.");

    let expected = "1bac0100e46abf3d120a43e97848264d2ced53df3bacf1885e82d9176b36fd4fdde407d5b59bb4\
        06c8977579a6591c4d0e25dd666f740a336d2a5d56ecef80f17cdbf232bc60067e0a50d0b3819a5ce67b8ef\
        2ba48f6634af4654f09faed8962ccdd692c7dd6c53170a9bfa3e5c50c5bc6449d7cf16c9657042ece1b4e7c8\
        2e42a5ac25bf387403de3e7851d22b094db8ca87c1228df99f8c2f7246d5844650d9413ff46a604abefaa70c\
        be6f3c56613eac53e540bcfacae00b6f3dc2ce61bc51640cb27d57ac9ff0fdb02cde64015821fe7f64015707\
        3909628922b1191c4a6bb151634e14eabba528bec5cf8db67473afbfab86404d4e26d337ca7a200a84ec4ff48\
        2010d8f18633d2e92b905c801803a2f659113a8c8227c3";

    assert_eq!(expected, hex::encode(brotli_compressed_msgpack));

    let json_serialized_result = serde_json::to_string_pretty(&config);
    assert!(json_serialized_result.is_ok());
    let json_serialized = json_serialized_result.unwrap();
    let expected = serde_json::json!({
      "input": {
        "type": "s3_object_metadata",
        "bucket": "yscope",
        "region_code": "us-east-2",
        "key_prefix": "sample-logs/cockroachdb.clp.zst",
        "endpoint_url": null,
        "aws_authentication": {
          "type": "credentials",
          "credentials": {
            "access_key_id": "ACCESS_KEY_ID",
            "secret_access_key": "SECRET_ACCESS_KEY"
          }
        },
        "ingestion_job_id": 1,
        "s3_object_metadata_ids": [],
        "dataset": "test-dataset",
        "timestamp_key": "timestamp",
        "unstructured": false
      },
      "output": {
        "target_uncompressed_size": 268_435_456,
        "clp_s": {
          "target_encoded_size": 301_989_888
        },
        "compression_level": 3
      }
    });
    let actual: Value = serde_json::from_str(json_serialized.as_str())
        .expect("The serialization result should be a valid JSON string.");
    assert_eq!(expected, actual);
}
