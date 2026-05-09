#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

# Mimics the relevant parts of .common-env.sh

# Default image — override with env var if needed
if [[ -z "${DEBUG_IMAGE:-}" ]]; then
    # Use the same image the real CLP package uses if set
    if [[ -n "${CLP_PACKAGE_CONTAINER_IMAGE_REF:-}" ]]; then
        export DEBUG_IMAGE="$CLP_PACKAGE_CONTAINER_IMAGE_REF"
    else
        echo "Set DEBUG_IMAGE to a Python Docker image, e.g.:"
        echo "  export DEBUG_IMAGE=python:3.12-slim"
        exit 1
    fi
fi

# Mimic the interactivity detection from the real .common-env.sh
CLP_COMPOSE_RUN_EXTRA_FLAGS=()
if [ ! -t 0 ]; then
    CLP_COMPOSE_RUN_EXTRA_FLAGS+=(--interactive=false)
else
    CLP_COMPOSE_RUN_EXTRA_FLAGS+=(--interactive --tty)
fi
