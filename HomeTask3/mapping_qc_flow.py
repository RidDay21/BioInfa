#!/usr/bin/env python3
"""
mapping_qc_flow.py — Mapping Quality Assessment Pipeline (Metaflow)

Implements the algorithm from Homework 3:
  FastQC → minimap2 → samtools view → samtools flagstat
  → parse %mapped → if >90%: samtools sort → freebayes → Finished
                    else: not OK

Usage:
  python mapping_qc_flow.py run \
      --fastq sample.fastq.gz \
      --ref reference.fa \
      --sample my_sample \
      --threads 4

Visualize DAG:
  python mapping_qc_flow.py output-dot | dot -Tpng -o dag.png
"""

import os
import subprocess
import re

from metaflow import FlowSpec, Parameter, step


MAPPED_THRESHOLD = 90  # percent


def run(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command, print it, and raise on error."""
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, text=True,
                            capture_output=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed (exit {result.returncode}): {cmd}")
    return result


def parse_pct_mapped(flagstat_path: str) -> float:
    """Parse % mapped from a samtools flagstat output file."""
    with open(flagstat_path) as fh:
        for line in fh:
            if " mapped (" in line:
                m = re.search(r'\((\d+(?:\.\d+)?)%', line)
                if m:
                    return float(m.group(1))
    raise ValueError(f"Could not parse mapped % from {flagstat_path}")


class MappingQCFlow(FlowSpec):

    fastq = Parameter("fastq",
                       help="Input FASTQ file (ONT reads)",
                       default="sample.fastq.gz")

    ref = Parameter("ref",
                    help="Reference genome FASTA",
                    default="reference.fa")

    sample = Parameter("sample",
                       help="Sample name prefix",
                       default="sample")

    threads = Parameter("threads",
                        help="Number of threads",
                        default=4,
                        type=int)

    # ------------------------------------------------------------------ start
    @step
    def start(self):
        """Initialize directories and parameters."""
        os.makedirs("results", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        print(f"Starting MappingQCFlow for sample: {self.sample}")
        print(f"  FASTQ     : {self.fastq}")
        print(f"  Reference : {self.ref}")
        self.next(self.fastqc)

    # ----------------------------------------------------------------- fastqc
    @step
    def fastqc(self):
        """Run FastQC on the input reads."""
        run(f"fastqc {self.fastq} -o results/ -t {self.threads}")

        # Rename QC-report
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        for fname in os.listdir("results"):
            if fname.endswith("_fastqc.html"):
                src = os.path.join("results", fname)
                dst = os.path.join("results", f"{self.sample}_QC_{ts}.html")
                os.rename(src, dst)
                print(f"  QC-report renamed to: {dst}")
                break

        self.next(self.index_ref)

    # -------------------------------------------------------------- index_ref
    @step
    def index_ref(self):
        """Index the reference genome with minimap2 (ONT preset)."""
        self.ref_index = f"{self.ref}.mmi"
        if not os.path.exists(self.ref_index):
            run(f"minimap2 -d {self.ref_index} {self.ref}")
        else:
            print(f"  Index already exists: {self.ref_index}")
        self.next(self.map_reads)

    # -------------------------------------------------------------- map_reads
    @step
    def map_reads(self):
        """Map ONT reads to reference using minimap2 (map-ont preset)."""
        self.sam = f"results/{self.sample}.sam"
        run(f"minimap2 -ax map-ont -t {self.threads} "
            f"{self.ref_index} {self.fastq} > {self.sam}")
        self.next(self.sam_to_bam)

    # ------------------------------------------------------------- sam_to_bam
    @step
    def sam_to_bam(self):
        """Convert SAM to BAM with samtools view."""
        self.bam = f"results/{self.sample}.bam"
        run(f"samtools view -bS -@ {self.threads} {self.sam} -o {self.bam}")
        self.next(self.flagstat)

    # --------------------------------------------------------------- flagstat
    @step
    def flagstat(self):
        """Run samtools flagstat and parse % mapped."""
        self.flagstat_file = f"results/{self.sample}_flagstat.txt"
        run(f"samtools flagstat {self.bam} > {self.flagstat_file}")

        self.pct_mapped = parse_pct_mapped(self.flagstat_file)
        print(f"  Mapped: {self.pct_mapped}%")
        self.next(self.quality_check)

    # ---------------------------------------------------------- quality_check
    @step
    def quality_check(self):
        """Decide OK / not OK based on % mapped threshold."""
        self.mapping_ok = self.pct_mapped > MAPPED_THRESHOLD
        
        # Создаем строковую переменную для переключателя (Switch)
        self.status_key = "ok" if self.mapping_ok else "not_ok"
        
        if self.mapping_ok:
            print(f"  {self.pct_mapped}% > {MAPPED_THRESHOLD}% → OK")
        else:
            print(f"  {self.pct_mapped}% <= {MAPPED_THRESHOLD}% → not OK")
        
        # Официальный синтаксис условного перехода в Metaflow:
        self.next({"ok": self.sort_bam, "not_ok": self.write_not_ok}, condition='status_key')

    # --------------------------------------------------------------- sort_bam
    @step
    def sort_bam(self):
        """Sort BAM with samtools sort (only if mapping is OK)."""
        self.sorted_bam = f"results/{self.sample}.sorted.bam"
        run(f"samtools sort -@ {self.threads} {self.bam} -o {self.sorted_bam}")
        run(f"samtools index {self.sorted_bam}")
        self.next(self.call_variants)

    # ---------------------------------------------------------- call_variants
    @step
    def call_variants(self):
        """Call genetic variants with freebayes."""
        self.vcf = f"results/{self.sample}.vcf"
        run(f"freebayes -f {self.ref} {self.sorted_bam} > {self.vcf}")
        self.next(self.write_ok)

    # --------------------------------------------------------------- write_ok
    @step
    def write_ok(self):
        """Write OK result and finish."""
        result_file = f"results/{self.sample}_result.txt"
        with open(result_file, "w") as fh:
            fh.write(f"RESULT: OK\n")
            fh.write(f"Mapped: {self.pct_mapped}%\n")
            fh.write(f"VCF: {self.vcf}\n")
        print(">>> Write OK")
        print(">>> Write Finished")
        self.next(self.end)

    # ------------------------------------------------------------ write_not_ok
    @step
    def write_not_ok(self):
        """Write not OK result."""
        result_file = f"results/{self.sample}_result.txt"
        with open(result_file, "w") as fh:
            fh.write(f"RESULT: not OK\n")
            fh.write(f"Mapped: {self.pct_mapped}%\n")
        print(">>> Write not OK")
        self.next(self.end)

    # -------------------------------------------------------------------- end
    @step
    def end(self):
        """Pipeline complete."""
        status = "OK" if self.mapping_ok else "not OK"
        print(f"MappingQCFlow finished. Status: {status}")


if __name__ == "__main__":
    MappingQCFlow()
