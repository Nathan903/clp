import {join} from "node:path";

import {FastifyPluginAsyncTypebox} from "@fastify/type-provider-typebox";
import {CLP_STORAGE_ENGINES} from "@webui/common/config";
import {
    ClpIoConfig,
    ClpIoFsInputConfig,
    CompressionJobCreationSchema,
    CompressionJobInputType,
    CompressionJobSchema,
} from "@webui/common/schemas/compression";
import {ErrorSchema} from "@webui/common/schemas/error";
import {constants} from "http2";

import {
    publicSettings,
    serverSettings,
} from "../../../settings.js";
import {CONTAINER_INPUT_LOGS_ROOT_DIR} from "./typings.js";


/**
 * Default compression job configuration.
 */
const DEFAULT_COMPRESSION_JOB_CONFIG: ClpIoConfig = Object.freeze({
    input: {
        dataset: null,
        path_prefix_to_remove: CONTAINER_INPUT_LOGS_ROOT_DIR,
        paths_to_compress: [],
        timestamp_key: null,
        type: CompressionJobInputType.FS,
        unstructured: true,
    },
    output: {
        compression_level: serverSettings.ArchiveOutputCompressionLevel,
        target_archive_size: serverSettings.ArchiveOutputTargetArchiveSize,
        target_dictionaries_size: serverSettings.ArchiveOutputTargetDictionariesSize,
        target_encoded_file_size: serverSettings.ArchiveOutputTargetEncodedFileSize,
        target_segment_size: serverSettings.ArchiveOutputTargetSegmentSize,
    },
});

type JobBody = {
    paths: string[];
    dataset?: string;
    timestampKey?: string;
    unstructured?: boolean;
    targetArchiveSize?: number;
    targetDictionariesSize?: number;
    targetEncodedFileSize?: number;
    targetSegmentSize?: number;
};

/**
 * Builds the compression job configuration from the request body.
 *
 * @param body
 * @param logError
 * @return The compression job configuration.
 */
const buildJobConfig = (
    body: JobBody,
    logError: (msg: string) => void
): ClpIoConfig => {
    const jobConfig: ClpIoConfig = structuredClone(DEFAULT_COMPRESSION_JOB_CONFIG);

    if ("number" === typeof body.targetArchiveSize) {
        jobConfig.output.target_archive_size = body.targetArchiveSize;
    }
    if ("number" === typeof body.targetDictionariesSize) {
        jobConfig.output.target_dictionaries_size = body.targetDictionariesSize;
    }
    if ("number" === typeof body.targetEncodedFileSize) {
        jobConfig.output.target_encoded_file_size = body.targetEncodedFileSize;
    }
    if ("number" === typeof body.targetSegmentSize) {
        jobConfig.output.target_segment_size = body.targetSegmentSize;
    }

    // eslint-disable-next-line no-warning-comments
    // TODO: Add support for S3 input
    (jobConfig.input as ClpIoFsInputConfig).paths_to_compress = body.paths.map(
        (path) => join(publicSettings.LogsInputRootDir ?? "", path)
    );

    if (CLP_STORAGE_ENGINES.CLP_S === publicSettings.ClpStorageEngine) {
        jobConfig.input.unstructured = false;
        if ("string" !== typeof body.dataset || 0 === body.dataset.length) {
            logError("Unable to submit compression job to the SQL database");
        } else {
            jobConfig.input.dataset = body.dataset;
        }
        if ("undefined" !== typeof body.timestampKey) {
            jobConfig.input.timestamp_key = body.timestampKey;
        }
        if (true === body.unstructured) {
            jobConfig.input.unstructured = true;
        }
    }

    return jobConfig;
};

/**
 * Compression API routes.
 *
 * @param fastify
 */
const plugin: FastifyPluginAsyncTypebox = async (fastify) => {
    const {CompressionJobDbManager} = fastify;

    /**
     * Submits a compression job and initiates the compression process.
     */
    fastify.post(
        "/",
        {
            schema: {
                body: CompressionJobCreationSchema,
                response: {
                    [constants.HTTP_STATUS_CREATED]: CompressionJobSchema,
                    [constants.HTTP_STATUS_INTERNAL_SERVER_ERROR]: ErrorSchema,
                },
                tags: ["Compression"],
            },
        },
        async (request, reply) => {
            const jobConfig = buildJobConfig(
                request.body,
                (msg: string) => {
                    request.log.error(msg);
                }
            );

            try {
                const jobId = await CompressionJobDbManager.submitJob(jobConfig);
                reply.code(constants.HTTP_STATUS_CREATED);

                return {jobId};
            } catch (err: unknown) {
                const errMsg = "Unable to submit compression job to the SQL database";
                request.log.error(err, errMsg);

                return reply.internalServerError(errMsg);
            }
        }
    );
};

export default plugin;
