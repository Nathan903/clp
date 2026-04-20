#ifndef CLP_S_TIMESTAMPDICTIONARYWRITER_HPP
#define CLP_S_TIMESTAMPDICTIONARYWRITER_HPP

#include <cstdint>
#include <map>
#include <sstream>
#include <string>
#include <string_view>
#include <system_error>
#include <unordered_map>
#include <utility>

#include <ystdlib/error_handling/Result.hpp>

#include <clp_s/timestamp_parser/TimestampParser.hpp>

#include "SchemaTree.hpp"
#include "TimestampEntry.hpp"
#include "TraceableException.hpp"

namespace clp_s {
class TimestampDictionaryWriter {
public:
    // Constructors
    TimestampDictionaryWriter() = default;

    /**
     * @return A Result containing the new TimestampDictionaryWriter, or an error code indicating the
     * failure.
     */
    [[nodiscard]] static auto create()
            -> ystdlib::error_handling::Result<TimestampDictionaryWriter>;

    /**
     * Writes the timestamp dictionary to a buffered stream.
     * @param stream
     */
    void write(std::stringstream& stream);

    /**
     * Ingests a timestamp entry from a string.
     * @param key
     * @param node_id
     * @param timestamp
     * @param is_json_literal
     * @return A Result containing a pair of the timestamp in epoch nanoseconds and pattern ID, or an
     * error code indicating the failure.
     */
    [[nodiscard]] auto ingest_string_timestamp(
            std::string_view key,
            int32_t node_id,
            std::string_view timestamp,
            bool is_json_literal
    ) -> ystdlib::error_handling::Result<std::pair<epochtime_t, uint64_t>>;

    /**
     * Ingests a numeric JSON entry.
     * @param key
     * @param node_id
     * @param timestamp
     * @return A Result containing a pair of the timestamp in epoch nanoseconds and pattern ID, or an
     * error code indicating the failure.
     */
    [[nodiscard]] auto
    ingest_numeric_json_timestamp(std::string_view key, int32_t node_id, std::string_view timestamp)
            -> ystdlib::error_handling::Result<std::pair<epochtime_t, uint64_t>>;

    /**
     * Ingests an unknown precision epoch timestamp.
     * @param key
     * @param node_id
     * @param timestamp
     * @return A Result containing a pair of the timestamp in epoch nanoseconds and pattern ID, or an
     * error code indicating the failure.
     */
    [[nodiscard]] auto ingest_unknown_precision_epoch_timestamp(
            std::string_view key,
            int32_t node_id,
            int64_t timestamp
    ) -> ystdlib::error_handling::Result<std::pair<epochtime_t, uint64_t>>;

    /**
     * @return The beginning of this archive's time range as milliseconds since the UNIX epoch
     */
    epochtime_t get_begin_timestamp() const;

    /**
     * @return The end of this archive's time range as milliseconds since the UNIX epoch
     */
    epochtime_t get_end_timestamp() const;

    /**
     * Clears and resets all internal state.
     */
    void clear();

private:
    // Variables
    std::vector<std::pair<timestamp_parser::TimestampPattern, uint64_t>>
            m_string_pattern_and_id_pairs;
    absl::flat_hash_map<std::string, std::pair<timestamp_parser::TimestampPattern, uint64_t>>
            m_numeric_pattern_to_id;
    uint64_t m_next_id{};

    std::unordered_map<int32_t, TimestampEntry> m_column_id_to_range;

    std::string m_generated_pattern;
    std::vector<timestamp_parser::TimestampPattern> m_quoted_timestamp_patterns;
    std::vector<timestamp_parser::TimestampPattern> m_numeric_timestamp_patterns;
};
}  // namespace clp_s

#endif  // CLP_S_TIMESTAMPDICTIONARYWRITER_HPP
