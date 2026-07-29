use serde::{
    Deserialize,
    Deserializer,
    de::{Error as _, IgnoredAny},
};

use crate::clp_config::{AwsAuthentication, S3Config};

/// Mirror of `clp_py_utils.clp_config.ClpConfig`.
///
/// # NOTE
///
/// * This type is partially defined: unused fields are omitted and discarded through
///   deserialization.
/// * The default values must be kept in sync with the Python definition.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(default)]
pub struct Config {
    pub package: Package,
    pub database: Database,
    pub results_cache: ResultsCache,
    pub api_server: Option<ApiServer>,
    pub log_ingestor: Option<LogIngestor>,
    pub logs_directory: String,
    pub stream_output: StreamOutput,
    pub logs_input: LogsInput,
    pub archive_output: ArchiveOutput,
    pub telemetry: Telemetry,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            package: Package::default(),
            database: Database::default(),
            results_cache: ResultsCache::default(),
            api_server: None,
            log_ingestor: None,
            logs_directory: "var/log".to_owned(),
            stream_output: StreamOutput::default(),
            logs_input: LogsInput::Fs {
                config: FsIngestion::default(),
            },
            archive_output: ArchiveOutput::default(),
            telemetry: Telemetry::default(),
        }
    }
}

/// Database names for CLP components.
///
/// # NOTE
///
///
/// This struct mirrors all allowed DB names from `clp_py_utils.clp_config.ClpDbNameType`. Instead
/// of storing them in a map, we use a struct to ensure all expected names are always present and
/// reject all unknown fields.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct ClpDbNames {
    pub clp: String,
    pub spider: String,
}

impl Default for ClpDbNames {
    fn default() -> Self {
        Self {
            clp: "clp-db".to_owned(),
            spider: "spider-db".to_owned(),
        }
    }
}

/// Mirror of `clp_py_utils.clp_config.Database`.
///
/// # NOTE
///
/// * This type is partially defined: unused fields are omitted and discarded through
///   deserialization.
/// * The default values must be kept in sync with the Python definition.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(default)]
pub struct Database {
    pub host: String,
    pub port: u16,
    pub names: ClpDbNames,
}

impl Default for Database {
    fn default() -> Self {
        Self {
            host: "localhost".to_owned(),
            port: 3306,
            names: ClpDbNames::default(),
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(default)]
pub struct ApiServer {
    pub host: String,
    pub port: u16,
    pub query_job_polling: QueryJobPollingConfig,
    pub default_max_num_query_results: u32,
}

impl Default for ApiServer {
    fn default() -> Self {
        Self {
            host: "localhost".to_owned(),
            port: 3001,
            query_job_polling: QueryJobPollingConfig::default(),
            default_max_num_query_results: 1000,
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(default)]
pub struct QueryJobPollingConfig {
    #[serde(rename = "initial_backoff")]
    pub initial_backoff_ms: u64,

    #[serde(rename = "max_backoff")]
    pub max_backoff_ms: u64,
}

impl Default for QueryJobPollingConfig {
    fn default() -> Self {
        Self {
            initial_backoff_ms: 100,
            max_backoff_ms: 5000,
        }
    }
}

/// Mirror of `clp_py_utils.clp_config.Package`.
///
/// # NOTE
///
/// * This type is partially defined: unused fields are omitted and discarded through
///   deserialization.
/// * The default values must be kept in sync with the Python definition.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(default)]
pub struct Package {
    pub storage_engine: StorageEngine,
}

impl Default for Package {
    fn default() -> Self {
        Self {
            storage_engine: StorageEngine::ClpS,
        }
    }
}

/// Mirror of `clp_py_utils.clp_config.StorageEngine`.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
pub enum StorageEngine {
    #[serde(rename = "clp")]
    Clp,
    #[serde(rename = "clp-s")]
    ClpS,
}

/// Mirror of `clp_py_utils.clp_config.ResultsCache`.
///
/// # NOTE
///
/// * This type is partially defined: unused fields are omitted and discarded through
///   deserialization.
/// * The default values must be kept in sync with the Python definition.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(default)]
pub struct ResultsCache {
    pub host: String,
    pub port: u16,
    pub db_name: String,
}

impl Default for ResultsCache {
    fn default() -> Self {
        Self {
            host: "localhost".to_owned(),
            port: 27017,
            db_name: "clp-query-results".to_owned(),
        }
    }
}

/// Mirror of `clp_py_utils.clp_config.StreamOutput`.
///
/// # NOTE
///
/// * The default values must be kept in sync with the Python definition.
#[derive(Clone, Default, Debug, Deserialize, Eq, PartialEq)]
#[serde(default)]
pub struct StreamOutput {
    pub storage: StreamOutputStorage,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(tag = "type")]
pub enum StreamOutputStorage {
    #[serde(rename = "fs")]
    Fs { directory: String },

    #[serde(rename = "s3")]
    S3 {
        staging_directory: String,
        s3_config: S3Config,
    },
}

impl Default for StreamOutputStorage {
    fn default() -> Self {
        Self::Fs {
            directory: "var/data/streams".to_owned(),
        }
    }
}

/// Mirror of `clp_py_utils.clp_config.LogIngestor`.
///
/// # NOTE
///
/// * The default values must be kept in sync with the Python definition.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(default)]
pub struct LogIngestor {
    pub host: String,
    pub port: u16,
    pub logging_level: String,
}

impl Default for LogIngestor {
    fn default() -> Self {
        Self {
            host: "localhost".to_owned(),
            port: 3002,
            logging_level: "INFO".to_owned(),
        }
    }
}

/// Mirror of `clp_py_utils.clp_config.ArchiveOutput`.
///
/// # NOTE
///
/// * This type is partially defined: unused fields are omitted and discarded through
///   deserialization.
/// * The default values must be kept in sync with the Python definition.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ArchiveOutput {
    pub target_uncompressed_size: u64,
    pub clp_s: ClpSArchiveOutput,
    pub compression_level: u8,
}

#[derive(Default)]
enum Present<T> {
    #[default]
    Missing,
    Null,
    Value(T),
}

impl<T> Present<T> {
    const fn is_present(&self) -> bool {
        !matches!(self, Self::Missing)
    }

    const fn is_null(&self) -> bool {
        matches!(self, Self::Null)
    }

    fn into_option(self) -> Option<T> {
        match self {
            Self::Missing | Self::Null => None,
            Self::Value(value) => Some(value),
        }
    }
}

fn deserialize_present<'de, D, T>(deserializer: D) -> Result<Present<T>, D::Error>
where
    D: Deserializer<'de>,
    T: Deserialize<'de>, {
    Option::<T>::deserialize(deserializer)
        .map(|value| value.map_or_else(|| Present::Null, Present::Value))
}

#[derive(Default, Deserialize)]
struct RawArchiveOutput {
    #[serde(default, deserialize_with = "deserialize_present")]
    target_uncompressed_size: Present<u64>,
    #[serde(default, deserialize_with = "deserialize_present")]
    clp: Present<IgnoredAny>,
    #[serde(default, deserialize_with = "deserialize_present")]
    clp_s: Present<ClpSArchiveOutput>,
    #[serde(default, deserialize_with = "deserialize_present")]
    target_archive_size: Present<u64>,
    #[serde(default, deserialize_with = "deserialize_present")]
    target_dictionaries_size: Present<u64>,
    #[serde(default, deserialize_with = "deserialize_present")]
    target_encoded_file_size: Present<u64>,
    #[serde(default, deserialize_with = "deserialize_present")]
    target_segment_size: Present<u64>,
    #[serde(default, deserialize_with = "deserialize_present")]
    compression_level: Present<u8>,
}

impl<'de> Deserialize<'de> for ArchiveOutput {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>, {
        let raw = RawArchiveOutput::deserialize(deserializer)?;
        let has_canonical_fields = raw.target_uncompressed_size.is_present()
            || raw.clp.is_present()
            || raw.clp_s.is_present();
        let has_legacy_fields = raw.target_archive_size.is_present()
            || raw.target_dictionaries_size.is_present()
            || raw.target_encoded_file_size.is_present()
            || raw.target_segment_size.is_present();
        if has_canonical_fields && has_legacy_fields {
            return Err(D::Error::custom(
                "legacy and canonical archive output fields cannot be mixed",
            ));
        }
        if raw.target_uncompressed_size.is_null()
            || raw.clp.is_null()
            || raw.clp_s.is_null()
            || raw.target_archive_size.is_null()
            || raw.target_dictionaries_size.is_null()
            || raw.target_encoded_file_size.is_null()
            || raw.target_segment_size.is_null()
            || raw.compression_level.is_null()
        {
            return Err(D::Error::custom("archive output fields cannot be null"));
        }

        let defaults = Self::default();
        let compression_level = raw
            .compression_level
            .into_option()
            .unwrap_or(defaults.compression_level);
        if !(1..=19).contains(&compression_level) {
            return Err(D::Error::custom(
                "archive output compression level must be between 1 and 19",
            ));
        }

        if has_legacy_fields {
            if raw.target_encoded_file_size.is_present()
                && 0 == raw.target_encoded_file_size.into_option().unwrap()
            {
                return Err(D::Error::custom("archive output sizes must be positive"));
            }
            let target_dictionaries_size = raw
                .target_dictionaries_size
                .into_option()
                .unwrap_or(32 * 1024 * 1024);
            let target_segment_size = raw
                .target_segment_size
                .into_option()
                .unwrap_or(256 * 1024 * 1024);
            if 0 == target_dictionaries_size || 0 == target_segment_size {
                return Err(D::Error::custom("archive output sizes must be positive"));
            }
            let target_encoded_size = target_dictionaries_size
                .checked_add(target_segment_size)
                .ok_or_else(|| D::Error::custom("CLP-S target encoded size overflows u64"))?;
            let target_uncompressed_size = raw
                .target_archive_size
                .into_option()
                .unwrap_or(defaults.target_uncompressed_size);
            if 0 == target_uncompressed_size {
                return Err(D::Error::custom("archive output sizes must be positive"));
            }
            return Ok(Self {
                target_uncompressed_size,
                clp_s: ClpSArchiveOutput {
                    target_encoded_size,
                },
                compression_level,
            });
        }

        let target_uncompressed_size = raw
            .target_uncompressed_size
            .into_option()
            .unwrap_or(defaults.target_uncompressed_size);
        let clp_s = raw.clp_s.into_option().unwrap_or(defaults.clp_s);
        if 0 == target_uncompressed_size || 0 == clp_s.target_encoded_size {
            return Err(D::Error::custom("archive output sizes must be positive"));
        }
        Ok(Self {
            target_uncompressed_size,
            clp_s,
            compression_level,
        })
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(default)]
pub struct ClpSArchiveOutput {
    pub target_encoded_size: u64,
}

impl Default for ClpSArchiveOutput {
    fn default() -> Self {
        Self {
            target_encoded_size: 288 * 1024 * 1024,
        }
    }
}

impl Default for ArchiveOutput {
    fn default() -> Self {
        Self {
            target_uncompressed_size: 256 * 1024 * 1024,
            clp_s: ClpSArchiveOutput::default(),
            compression_level: 3,
        }
    }
}

/// Mirror of `clp_py_utils.clp_config.S3IngestionConfig`.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
pub struct S3Ingestion {
    pub aws_authentication: AwsAuthentication,
}

/// Mirror of `clp_py_utils.clp_config.FsIngestionConfig`.
///
/// # NOTE
///
/// * The default values must be kept in sync with the Python definition.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
pub struct FsIngestion {
    pub directory: String,
}

impl Default for FsIngestion {
    fn default() -> Self {
        Self {
            directory: "/".to_owned(),
        }
    }
}

/// Mirror of `clp_py_utils.clp_config.ClpConfig.logs_input`.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(tag = "type")]
pub enum LogsInput {
    #[serde(rename = "fs")]
    Fs {
        #[serde(flatten)]
        config: FsIngestion,
    },

    #[serde(rename = "s3")]
    S3 {
        #[serde(flatten)]
        config: S3Ingestion,
    },
}

/// Mirror of `clp_py_utils.clp_config.Telemetry`.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(default)]
pub struct Telemetry {
    pub disable: bool,
    pub endpoint: String,
}

impl Default for Telemetry {
    fn default() -> Self {
        Self {
            disable: false,
            endpoint: "https://telemetry.yscope.io".to_owned(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{ArchiveOutput, ClpSArchiveOutput, LogsInput};

    #[test]
    fn deserialize_canonical_archive_output() {
        let archive_output = serde_json::from_value::<ArchiveOutput>(serde_json::json!({
            "target_uncompressed_size": 100,
            "clp_s": {"target_encoded_size": 60},
            "compression_level": 5,
        }))
        .expect("failed to deserialize canonical `ArchiveOutput`");

        assert_eq!(
            ArchiveOutput {
                target_uncompressed_size: 100,
                clp_s: ClpSArchiveOutput {
                    target_encoded_size: 60,
                },
                compression_level: 5,
            },
            archive_output
        );
    }

    #[test]
    fn deserialize_legacy_archive_output() {
        let archive_output = serde_json::from_value::<ArchiveOutput>(serde_json::json!({
            "target_archive_size": 100,
            "target_dictionaries_size": 20,
            "target_encoded_file_size": 30,
            "target_segment_size": 40,
            "compression_level": 5,
        }))
        .expect("failed to deserialize legacy `ArchiveOutput`");

        assert_eq!(
            ArchiveOutput {
                target_uncompressed_size: 100,
                clp_s: ClpSArchiveOutput {
                    target_encoded_size: 60,
                },
                compression_level: 5,
            },
            archive_output
        );
    }

    #[test]
    fn deserialize_partial_legacy_archive_output() {
        let archive_output = serde_json::from_value::<ArchiveOutput>(serde_json::json!({
            "target_segment_size": 40,
        }))
        .expect("failed to deserialize partial legacy `ArchiveOutput`");

        assert_eq!(256 * 1024 * 1024, archive_output.target_uncompressed_size);
        assert_eq!(
            32 * 1024 * 1024 + 40,
            archive_output.clp_s.target_encoded_size
        );
        assert_eq!(3, archive_output.compression_level);
    }

    #[test]
    fn reject_null_archive_output_fields() {
        for config in [
            serde_json::json!({"target_uncompressed_size": null}),
            serde_json::json!({"clp_s": null}),
            serde_json::json!({"compression_level": null}),
        ] {
            assert!(serde_json::from_value::<ArchiveOutput>(config).is_err());
        }
    }

    #[test]
    fn reject_non_positive_archive_output_sizes() {
        for config in [
            serde_json::json!({"target_uncompressed_size": 0}),
            serde_json::json!({"clp_s": {"target_encoded_size": 0}}),
            serde_json::json!({"target_archive_size": 0}),
            serde_json::json!({"target_dictionaries_size": 0}),
            serde_json::json!({"target_encoded_file_size": 0}),
            serde_json::json!({"target_segment_size": 0}),
        ] {
            assert!(serde_json::from_value::<ArchiveOutput>(config).is_err());
        }
    }

    #[test]
    fn reject_invalid_archive_output_compression_levels() {
        for compression_level in [0, 20] {
            let result = serde_json::from_value::<ArchiveOutput>(serde_json::json!({
                "compression_level": compression_level,
            }));
            assert!(result.is_err());
        }
    }

    #[test]
    fn reject_mixed_archive_output_fields() {
        for config in [
            serde_json::json!({
                "clp": {"target_segment_size": 40},
                "target_segment_size": 40,
            }),
            serde_json::json!({
                "clp_s": null,
                "target_segment_size": 40,
            }),
        ] {
            let result = serde_json::from_value::<ArchiveOutput>(config);

            assert!(result.is_err());
            assert!(
                result
                    .unwrap_err()
                    .to_string()
                    .contains("legacy and canonical archive output fields cannot be mixed")
            );
        }
    }

    #[test]
    fn reject_legacy_archive_output_encoded_size_overflow() {
        let result = serde_json::from_value::<ArchiveOutput>(serde_json::json!({
            "target_dictionaries_size": u64::MAX,
            "target_segment_size": 1,
        }));

        assert!(result.is_err());
        assert!(
            result
                .unwrap_err()
                .to_string()
                .contains("CLP-S target encoded size overflows u64")
        );
    }

    #[test]
    fn deserialize_logs_input_s3_config() {
        const ACCESS_KEY_ID: &str = "YSCOPE";
        const SECRET_ACCESS_KEY: &str = "IamSecret";
        let logs_input_config_json = serde_json::json!({
            "type": "s3",
            "aws_authentication": {
                "type": "credentials",
                "credentials": {
                    "access_key_id": ACCESS_KEY_ID,
                    "secret_access_key": SECRET_ACCESS_KEY,
                }
            }
        });

        let deserialized =
            serde_json::from_str::<LogsInput>(logs_input_config_json.to_string().as_str())
                .expect("failed to deserialize `LogsInput` from JSON");

        match deserialized {
            LogsInput::S3 { config } => match config.aws_authentication {
                crate::clp_config::AwsAuthentication::Credentials { credentials } => {
                    assert_eq!(credentials.access_key_id, ACCESS_KEY_ID);
                    assert_eq!(credentials.secret_access_key, SECRET_ACCESS_KEY);
                }
                crate::clp_config::AwsAuthentication::Default => {
                    panic!("Expected credentials, got `default`")
                }
            },
            LogsInput::Fs { .. } => panic!("Expected S3"),
        }
    }

    #[test]
    fn deserialize_logs_input_s3_default_config() {
        let logs_input_config_json = serde_json::json!({
            "type": "s3",
            "aws_authentication": {
                "type": "default",
            }
        });

        let deserialized =
            serde_json::from_str::<LogsInput>(logs_input_config_json.to_string().as_str())
                .expect("failed to deserialize `LogsInput` from JSON");

        match deserialized {
            LogsInput::S3 { config } => {
                assert_eq!(
                    config.aws_authentication,
                    crate::clp_config::AwsAuthentication::Default
                );
            }
            LogsInput::Fs { .. } => panic!("Expected S3"),
        }
    }

    #[test]
    fn deserialize_logs_input_fs_config() {
        const DIRECTORY: &str = "/var/logs";

        let logs_input_config_json = serde_json::json!({
            "type": "fs",
            "directory": DIRECTORY,
        });

        let deserialized =
            serde_json::from_str::<LogsInput>(logs_input_config_json.to_string().as_str())
                .expect("failed to deserialize `LogsInput` from JSON");

        match deserialized {
            LogsInput::Fs { config } => {
                assert_eq!(config.directory, DIRECTORY);
            }
            LogsInput::S3 { .. } => panic!("Expected Fs"),
        }
    }
}
