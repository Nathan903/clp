use tracing_appender::{
    non_blocking::{NonBlockingBuilder, WorkerGuard},
    rolling::{RollingFileAppender, Rotation},
};
use tracing_subscriber::{self, fmt::writer::MakeWriterExt};

/// Holds the [`WorkerGuard`]s for all non-blocking log writers so they are
/// flushed when the guard is dropped.
///
/// The guard must be held for the lifetime of the program; dropping it signals
/// the background worker threads to flush any buffered log records to their
/// underlying writers (stdout and/or the rolling file appender).
pub struct LoggingGuard {
    _guards: Vec<WorkerGuard>,
}

/// Initializes the global tracing subscriber with JSON-formatted output.
///
/// Logs are always written to stdout, and—if the `CLP_LOGS_DIR` environment
/// variable is set—also to an hourly rolling file (`log_filename`) in that
/// directory.
///
/// # Writer behavior
///
/// Every writer (stdout and the rolling file appender) is wrapped in a
/// **lossless** non-blocking writer via [`tracing_appender::non_blocking`].
/// This offloads log I/O to a dedicated background worker thread so that
/// emitting a log record does not block the calling task, as long as the
/// worker's channel has capacity. In lossless mode records are never dropped:
/// if the channel were to fill, the writer falls back to a synchronous
/// (blocking) write rather than discarding the record. In practice the
/// channel is unlikely to fill given the current log volume, so writes stay
/// non-blocking on the fast path.
///
/// This behavior is the same regardless of whether `CLP_LOGS_DIR` is set, so
/// logging latency does not implicitly depend on the output target.
///
/// The returned [`LoggingGuard`] must be held for the lifetime of the program
/// to ensure all buffered records are flushed on shutdown.
pub fn set_up_logging(log_filename: &str) -> LoggingGuard {
    let subscriber = tracing_subscriber::fmt()
        .event_format(
            tracing_subscriber::fmt::format()
                .with_level(true)
                .with_target(false)
                .with_file(true)
                .with_line_number(true)
                .json(),
        )
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .with_ansi(false);

    // Wrap stdout in a lossless non-blocking writer so log writes are
    // offloaded to a background worker thread rather than blocking the calling
    // task. The guard is retained in the returned `LoggingGuard` so the worker
    // is flushed on shutdown.
    let (non_blocking_stdout, stdout_guard) =
        NonBlockingBuilder::new().lossless(true).finish(std::io::stdout());
    let mut guards = vec![stdout_guard];

    let writer = if let Ok(logs_directory) = std::env::var("CLP_LOGS_DIR") {
        let logs_directory = std::path::Path::new(logs_directory.as_str());
        let file_appender =
            RollingFileAppender::new(Rotation::HOURLY, logs_directory, log_filename);
        let (non_blocking_file, file_guard) =
            NonBlockingBuilder::new().lossless(true).finish(file_appender);
        guards.push(file_guard);
        non_blocking_stdout.and(non_blocking_file)
    } else {
        non_blocking_stdout
    };

    subscriber.with_writer(writer).init();
    LoggingGuard { _guards: guards }
}