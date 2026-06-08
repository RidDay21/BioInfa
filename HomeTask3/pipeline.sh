#!/usr/bin/env bash
# =============================================================================
# Homework 3: Genetic Variant Calling Pipeline (bash implementation)
# Tools: minimap2, samtools, FastQC, freebayes
# Sequencing: Oxford Nanopore (ONT) long reads
# =============================================================================

set -euo pipefail

# ---------- CONFIG -----------------------------------------------------------
FASTQ="${1:-sample.fastq.gz}"          # input reads (ONT)
REF="${2:-reference.fa}"               # reference genome (e.coli or hg38)
SAMPLE="${3:-sample}"                  # sample name prefix
THREADS="${4:-4}"
MAPPED_THRESHOLD=90                    # % mapped threshold

RESULTS_DIR="results"
LOGS_DIR="logs"
mkdir -p "$RESULTS_DIR" "$LOGS_DIR"

LOG="$LOGS_DIR/pipeline.log"
exec > >(tee -a "$LOG") 2>&1

echo "============================================================"
echo " Pipeline started: $(date)"
echo " Input FASTQ : $FASTQ"
echo " Reference   : $REF"
echo " Sample      : $SAMPLE"
echo "============================================================"

# ---------- STEP 1: FastQC ---------------------------------------------------
echo "[1/7] Running FastQC..."
fastqc "$FASTQ" -o "$RESULTS_DIR/" -t "$THREADS"
echo "      FastQC done. Renaming QC-report..."
# Rename FastQC report to include sample name and timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
QC_HTML=$(ls "$RESULTS_DIR/"*_fastqc.html 2>/dev/null | head -1 || true)
if [[ -n "$QC_HTML" ]]; then
    mv "$QC_HTML" "$RESULTS_DIR/${SAMPLE}_QC_${TIMESTAMP}.html"
    echo "      QC-report saved as: ${SAMPLE}_QC_${TIMESTAMP}.html"
fi

# ---------- STEP 2: Index reference (if not already done) --------------------
echo "[2/7] Indexing reference with minimap2..."
if [[ ! -f "${REF}.mmi" ]]; then
    # ONT long reads: preset "map-ont"
    minimap2 -d "${REF}.mmi" "$REF"
    echo "      Index created: ${REF}.mmi"
else
    echo "      Index already exists, skipping."
fi

# ---------- STEP 3: Mapping with minimap2 (ONT preset) -----------------------
echo "[3/7] Mapping reads with minimap2 (ONT preset)..."
SAM="$RESULTS_DIR/${SAMPLE}.sam"
minimap2 -ax map-ont -t "$THREADS" "${REF}.mmi" "$FASTQ" > "$SAM"
echo "      Mapping done: $SAM"

# ---------- STEP 4: SAM -> BAM (samtools view) --------------------------------
echo "[4/7] Converting SAM to BAM (samtools view)..."
BAM="$RESULTS_DIR/${SAMPLE}.bam"
samtools view -bS -@ "$THREADS" "$SAM" -o "$BAM"
echo "      BAM created: $BAM"

# ---------- STEP 5: samtools flagstat + parse % mapped -----------------------
echo "[5/7] Running samtools flagstat..."
FLAGSTAT="$RESULTS_DIR/${SAMPLE}_flagstat.txt"
samtools flagstat "$BAM" > "$FLAGSTAT"
echo "      flagstat result:"
cat "$FLAGSTAT"

# Parse % mapped using the dedicated script
PCT_MAPPED=$(bash scripts/parse_flagstat.sh "$FLAGSTAT")
echo "      Mapped reads: ${PCT_MAPPED}%"

# ---------- STEP 6: Quality check OK / not OK --------------------------------
echo "[6/7] Quality assessment..."
# Use awk for float comparison (bc alternative)
IS_OK=$(awk -v pct="$PCT_MAPPED" -v thr="$MAPPED_THRESHOLD" \
        'BEGIN { print (pct+0 > thr+0) ? "YES" : "NO" }')

if [[ "$IS_OK" == "YES" ]]; then
    echo "      % mapped (${PCT_MAPPED}%) > ${MAPPED_THRESHOLD}% → OK"

    # ---------- STEP 6a: samtools sort ---------------------------------------
    echo "[6a]  Sorting BAM (samtools sort)..."
    SORTED_BAM="$RESULTS_DIR/${SAMPLE}.sorted.bam"
    samtools sort -@ "$THREADS" "$BAM" -o "$SORTED_BAM"
    samtools index "$SORTED_BAM"
    echo "      Sorted BAM: $SORTED_BAM"

    # ---------- STEP 6b: freebayes variant calling ---------------------------
    echo "[6b]  Calling variants with freebayes..."
    VCF="$RESULTS_DIR/${SAMPLE}.vcf"
    freebayes -f "$REF" "$SORTED_BAM" > "$VCF"
    echo "      VCF: $VCF"

    echo ""
    echo ">>> RESULT: OK"
    echo ">>> Pipeline finished: $(date)"
    echo ">>> Write Finished"
else
    echo "      % mapped (${PCT_MAPPED}%) <= ${MAPPED_THRESHOLD}% → not OK"
    echo ""
    echo ">>> RESULT: not OK"
    echo ">>> Pipeline finished: $(date)"
fi
