#!/bin/bash
########################################################################################################################
# 
# TriBench - Trino Benchmarking Framework
# Command Line Interface
#  
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#      http://www.apache.org/licenses/LICENSE-2.0
# 
########################################################################################################################

# Default configuration values
DEFAULT_PYTHON_ENV="tribench"
DEFAULT_JAVA_HOME="/usr/lib/jvm/java-11-openjdk"
DEFAULT_JAVA_OPTS="-Xmx2g"

########################################################################################################################
# PATHS AND CONFIG
########################################################################################################################

# Resolve links
this="$0"
while [ -h "$this" ]; do
  ls=`ls -ld "$this"`
  link=`expr "$ls" : '.*-> \(.*\)$'`
  if expr "$link" : '.*/.*' > /dev/null; then
    this="$link"
  else
    this=`dirname "$this"`/"$link"
  fi
done

# Convert relative path to absolute path
bin=`dirname "$this"`
script=`basename "$this"`
bin=`cd "$bin"; pwd`
this="$bin/$script"

# Define the main directory
TRIBENCH_ROOT_DIR=`dirname "$this"`
TRIBENCH_LIB_DIR=${TRIBENCH_ROOT_DIR}/lib
TRIBENCH_CONFIG_DIR=${TRIBENCH_ROOT_DIR}/config
TRIBENCH_LOG_DIR=${TRIBENCH_ROOT_DIR}/log

########################################################################################################################
# ENVIRONMENT VARIABLES
########################################################################################################################

# Define Python environment
if [ -z "${CONDA_DEFAULT_ENV}" ]; then
    echo "Activating conda environment: ${DEFAULT_PYTHON_ENV}"
    conda activate ${DEFAULT_PYTHON_ENV} 2>/dev/null || {
        echo "Warning: Could not activate conda environment '${DEFAULT_PYTHON_ENV}'"
        echo "Please ensure conda is installed and the environment exists:"
        echo "  conda env create -f environment.yml"
    }
fi

# Define JAVA_HOME if not set
if [ -z "${JAVA_HOME}" ]; then
    if [ "$(uname)" == "Darwin" ]; then
        # Mac OS X
        JAVA_HOME=$(/usr/libexec/java_home -v 11 2>/dev/null || echo "")
    else
        # Linux
        JAVA_HOME=${DEFAULT_JAVA_HOME}
    fi
fi

if [ -z "${TRIBENCH_JAVA_OPTS}" ]; then
    TRIBENCH_JAVA_OPTS="${DEFAULT_JAVA_OPTS}"
fi

########################################################################################################################
# COMMAND DISPATCH
########################################################################################################################

usage() {
    echo "TriBench - Trino Benchmarking Framework"
    echo ""
    echo "Usage: tribench COMMAND [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  sys setup <system>        Setup a system (trino, iceberg, minio)"
    echo "  sys teardown <system>     Teardown a system"
    echo "  sys status <system>       Check system status"
    echo ""  
    echo "  exp run <experiment>      Execute an experiment"
    echo "  exp list                  List available experiments"
    echo "  exp config <experiment>   Show experiment configuration"
    echo ""
    echo "  suite run <suite>         Execute all experiments in a suite"
    echo "  suite list                List available experiment suites"
    echo ""
    echo "  data generate <dataset>   Generate a dataset"
    echo "  data load <dataset>       Load a dataset into systems"
    echo "  data list                 List available datasets"
    echo ""
    echo "  res analyze <suite>       Analyze benchmark results"
    echo "  res export <suite>        Export results to CSV/JSON"
    echo "  res archive <suite>       Archive results to tar.gz"
    echo ""
    echo "  db:init                   Initialize results database"
    echo "  db:import <suite>         Import results into database"
    echo ""
    echo "  val:hosts                 Validate host configuration"
    echo "  val:systems               Validate system installations"
    echo ""
    echo "Examples:"
    echo "  tribench sys setup trino"
    echo "  tribench exp run tpch.sf1.query01"
    echo "  tribench suite run tpch.sf1"
    echo "  tribench res analyze tpch.sf1"
}

# Parse command
if [ $# -eq 0 ]; then
    usage
    exit 1
fi

COMMAND=$1
shift

case $COMMAND in
    sys:*)
        python3 ${TRIBENCH_ROOT_DIR}/lib/tribench/cli/system_commands.py "$COMMAND" "$@"
        ;;
    exp:*)
        python3 ${TRIBENCH_ROOT_DIR}/lib/tribench/cli/experiment_commands.py "$COMMAND" "$@"
        ;;
    suite:*)
        python3 ${TRIBENCH_ROOT_DIR}/lib/tribench/cli/suite_commands.py "$COMMAND" "$@"
        ;;
    data:*)
        python3 ${TRIBENCH_ROOT_DIR}/lib/tribench/cli/data_commands.py "$COMMAND" "$@"
        ;;
    res:*)
        python3 ${TRIBENCH_ROOT_DIR}/lib/tribench/cli/result_commands.py "$COMMAND" "$@"
        ;;
    db:*)
        python3 ${TRIBENCH_ROOT_DIR}/lib/tribench/cli/database_commands.py "$COMMAND" "$@"
        ;;
    val:*)
        python3 ${TRIBENCH_ROOT_DIR}/lib/tribench/cli/validation_commands.py "$COMMAND" "$@"
        ;;
    --help|-h|help)
        usage
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo ""
        usage
        exit 1
        ;;
esac
