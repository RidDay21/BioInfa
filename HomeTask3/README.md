# Homework 3: Genetic Variant Calling Pipeline

Студент: Лаптев Николай Николаевич 23215

---

## Выбранные инструменты

| Категория | Инструмент |
|---|---|
| Секвенирование | Oxford Nanopore (ONT) |
| Картирование | minimap2 |
| Фреймворк пайплайнов | Metaflow (Netflix) |

---

## Данные

* **Прочтения (NCBI SRA):** [SRR26117377](https://www.ncbi.nlm.nih.gov/sra/SRR26117377) (*Escherichia coli*, Oxford Nanopore)
* **Прямая ссылка на FASTQ архив (ENA):** [SRR26117377.fastq.gz](https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR261/077/SRR26117377/SRR26117377.fastq.gz)
* **Референсный геном (NCBI RefSeq):** [GCF_000005845.2_ASM584v2_genomic.fna.gz](https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/005/845/GCF_000005845.2_ASM584v2/GCF_000005845.2_ASM584v2_genomic.fna.gz)

---

## Расположение файлов и отчетов (Папка HomeTask3)

Все материалы лабораторной работы находятся в папке `HomeTask3` и распределены следующим образом:

* **Документация и графы:**
  * `README.md` — текущий файл.
  * `DAG_DESCRIPTION.md` — теоретическое описание графа пайплайна и его отличий от блок-схемы.
  * `METAFLOW_SETUP.md` — инструкция по работе с Metaflow.
  * `dag.png` и `dag_full.dot` — визуализация графа задач пайплайна.

* **Исполняемые скрипты:**
  * `pipeline.sh` — Bash-скрипт пайплайна.
  * `parse_flagstat.sh` — скрипт автоматического разбора логов.
  * `mapping_qc_flow.py` — основной пайплайн на Metaflow.
  * `hello_world.py` — тестовый скрипт Metaflow.

* **Результаты работы и отчеты (Папка `results/`):**
  * `results/sample_QC_*.html` — интерактивные HTML-отчеты контроля качества от утилиты FastQC.
  * `results/sample.bam` — итоговый бинарный файл выравнивания прочтений (исходный тяжелый SAM-файл удален для оптимизации размера репозитория).
  * `results/sample_flagstat.txt` — текстовый отчет со статистикой выравнивания от `samtools flagstat`.
  * `results/sample_result.txt` — финальный текстовый вердикт пайплайна.

---

## Анализ результатов контроля качества

Логи работы утилиты `samtools flagstat` (сохранены в `results/sample_flagstat.txt`):


```

5511971 + 0 in total (QC-passed reads + QC-failed reads)
5511971 + 0 primary
0 + 0 mapped (0.00% : N/A)

```

**Итоговый вердикт:** Процент картированных ридов составил **0.00%**. Шаг контроля качества зафиксировал, что значение находится ниже целевого порога в 90%. Пайплайн корректно обработал логику условного ветвления, остановил выполнение последующих шагов и завершил работу, создав отчет `results/sample_result.txt` со статусом **`RESULT: not OK`**.

```