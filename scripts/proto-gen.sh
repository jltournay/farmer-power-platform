#!/bin/bash
# Protocol Buffer Generation Script
# Generates Python stubs from .proto files into libs/fp-proto/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PROTO_DIR="${PROJECT_ROOT}/proto"
OUTPUT_DIR="${PROJECT_ROOT}/libs/fp-proto/src/fp_proto"

echo "=== Farmer Power Platform - Proto Generation ==="
echo "Proto source: ${PROTO_DIR}"
echo "Output dir: ${OUTPUT_DIR}"
echo ""

# Check if grpcio-tools is installed
if ! python -c "import grpc_tools.protoc" 2>/dev/null; then
    echo "Error: grpcio-tools not installed. Run: pip install grpcio-tools"
    exit 1
fi

# Clean previous generated files (but keep __init__.py)
echo "Cleaning previous generated files..."
find "${OUTPUT_DIR}" -name "*_pb2.py" -delete 2>/dev/null || true
find "${OUTPUT_DIR}" -name "*_pb2_grpc.py" -delete 2>/dev/null || true
find "${OUTPUT_DIR}" -name "*_pb2.pyi" -delete 2>/dev/null || true
find "${OUTPUT_DIR}" -name "*_pb2_grpc.pyi" -delete 2>/dev/null || true

# Generate for each domain
for domain_dir in "${PROTO_DIR}"/*/; do
    domain=$(basename "${domain_dir}")

    for version_dir in "${domain_dir}"*/; do
        version=$(basename "${version_dir}")

        # Create output directory structure
        out_subdir="${OUTPUT_DIR}/${domain}/${version}"
        mkdir -p "${out_subdir}"

        # Find all .proto files in this version directory
        proto_files=$(find "${version_dir}" -name "*.proto" 2>/dev/null || true)

        if [ -n "${proto_files}" ]; then
            echo "Generating: ${domain}/${version}"

            python -m grpc_tools.protoc \
                -I"${PROTO_DIR}" \
                -I"${PROJECT_ROOT}" \
                --python_out="${OUTPUT_DIR}" \
                --grpc_python_out="${OUTPUT_DIR}" \
                --pyi_out="${OUTPUT_DIR}" \
                ${proto_files}

            # Create __init__.py files if they don't exist
            domain_init="${OUTPUT_DIR}/${domain}/__init__.py"
            version_init="${out_subdir}/__init__.py"

            if [ ! -f "${domain_init}" ]; then
                cat > "${domain_init}" << EOF
"""${domain} domain Protocol Buffer stubs."""
EOF
            fi

            if [ ! -f "${version_init}" ]; then
                # Get all generated modules for this version
                pb2_files=$(find "${out_subdir}" -name "*_pb2.py" -exec basename {} .py \; 2>/dev/null | sort)
                grpc_files=$(find "${out_subdir}" -name "*_pb2_grpc.py" -exec basename {} .py \; 2>/dev/null | sort)

                cat > "${version_init}" << EOF
"""${domain} ${version} Protocol Buffer stubs.

Auto-generated from proto/${domain}/${version}/*.proto
DO NOT EDIT MANUALLY.
"""
EOF

                # Add imports to __init__.py
                for pb2 in ${pb2_files}; do
                    echo "from fp_proto.${domain}.${version}.${pb2} import *" >> "${version_init}"
                done
                for grpc in ${grpc_files}; do
                    echo "from fp_proto.${domain}.${version}.${grpc} import *" >> "${version_init}"
                done
            fi
        fi
    done
done

# Fix imports in generated files (protoc generates imports from proto package path, not Python package path)
echo ""
echo "Fixing imports in generated files..."
# Fix imports like "from plantation.v1 import" to "from fp_proto.plantation.v1 import"
# BUT exclude "from google." imports which should remain as standard library imports
for grpc_file in $(find "${OUTPUT_DIR}" -name "*_pb2_grpc.py"); do
    # Use a temp file approach for portability across macOS/Linux
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # Fix domain imports but NOT google.protobuf imports
        sed -i '' 's/from \(ai_model\)\.\([a-z0-9]*\) import/from fp_proto.\1.\2 import/g' "${grpc_file}"
        sed -i '' 's/from \(collection\)\.\([a-z0-9]*\) import/from fp_proto.\1.\2 import/g' "${grpc_file}"
        sed -i '' 's/from \(plantation\)\.\([a-z0-9]*\) import/from fp_proto.\1.\2 import/g' "${grpc_file}"
        sed -i '' 's/from \(common\)\.\([a-z0-9]*\) import/from fp_proto.\1.\2 import/g' "${grpc_file}"
        sed -i '' 's/from \(mcp\)\.\([a-z0-9]*\) import/from fp_proto.\1.\2 import/g' "${grpc_file}"
    else
        sed -i 's/from \(ai_model\)\.\([a-z0-9]*\) import/from fp_proto.\1.\2 import/g' "${grpc_file}"
        sed -i 's/from \(collection\)\.\([a-z0-9]*\) import/from fp_proto.\1.\2 import/g' "${grpc_file}"
        sed -i 's/from \(plantation\)\.\([a-z0-9]*\) import/from fp_proto.\1.\2 import/g' "${grpc_file}"
        sed -i 's/from \(common\)\.\([a-z0-9]*\) import/from fp_proto.\1.\2 import/g' "${grpc_file}"
        sed -i 's/from \(mcp\)\.\([a-z0-9]*\) import/from fp_proto.\1.\2 import/g' "${grpc_file}"
    fi
done

echo ""
echo "=== Proto generation complete ==="
echo ""
echo "Generated files:"
find "${OUTPUT_DIR}" -name "*.py" -o -name "*.pyi" | grep -E "(_pb2|_pb2_grpc)" | sort
