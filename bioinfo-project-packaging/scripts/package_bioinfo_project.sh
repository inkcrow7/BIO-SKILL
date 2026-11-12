#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: package_bioinfo_project.sh SOURCE_PROJECT [DESTINATION_DIRECTORY [ARCHIVE_BASENAME [EXTRA_EXCLUDE_PATTERN ...]]]" >&2
}

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

source_project=${1%/}
destination_dir=${2:-$source_project}
destination_dir=${destination_dir%/}
archive_basename=${3:-$(basename "$source_project")}
if [[ $# -ge 3 ]]; then
  shift 3
elif [[ $# -ge 2 ]]; then
  shift 2
else
  shift 1
fi
extra_exclude_patterns=("$@")

if [[ ! -d "$source_project" ]]; then
  echo "ERROR: source project is not a directory: $source_project" >&2
  exit 2
fi
if [[ ! -d "$source_project/Results" ]]; then
  echo "ERROR: source project has no Results directory: $source_project/Results" >&2
  exit 2
fi
if [[ ! -d "$destination_dir" ]]; then
  echo "ERROR: destination directory is not a directory: $destination_dir" >&2
  exit 2
fi
if [[ -z "$archive_basename" || "$archive_basename" == "." || "$archive_basename" == ".." || "$archive_basename" == */* ]]; then
  echo "ERROR: archive basename must be one safe path component" >&2
  exit 2
fi

source_parent=$(dirname "$source_project")
source_name=$(basename "$source_project")
archive_path="$destination_dir/$archive_basename.tgz"
checksum_path="$archive_path.sha256"

if [[ -e "$archive_path" || -e "$checksum_path" ]]; then
  echo "ERROR: target exists; preserve or remove it explicitly before rerun: $archive_path" >&2
  exit 3
fi

exclude_patterns=(
  'Data/Raw' 'Data/Raw/*' '*/Data/Raw' '*/Data/Raw/*'
  '*.h5ad' '*.h5ad.gz'
  '*.rds' '*.Rds' '*.RDS' '*.RData' '*.Rdata' '*.rdata'
  '*.log' '*loom' '*bam*' '*arrow*' '*.h5'
  'Save-Uwot-UMAP*tar' 'Impute-Weights*'
  '*.pkl' '*.pkl.gz' '*bgz' '*qs' '*qs2'
  '*.md' '*.mmd' '*.docx' '*.doc' '*.txt' '*manifest*'
  '*.html' '*.htm'
  '*gallery*' '*gallery*/*'
  '*Report.bundle_*' '*report_assets*' '*table_previews*' '*preview_resources*'
  'previews' 'previews/*' '*/previews' '*/previews/*'
  '*figure_index.tsv' '*file_index.tsv' 'index.tsv' 'index.csv' '*/index.tsv' '*/index.csv'
  '*run_summary*' '*.map' '*screenshots*' '*review_build*' '*draft*'
  '__pycache__' '__pycache__/*' '.cache' '.cache/*'
  '.pytest_cache' '.pytest_cache/*' '.ruff_cache' '.ruff_cache/*'
  '.mypy_cache' '.mypy_cache/*' '.ipynb_checkpoints' '.ipynb_checkpoints/*'
  '.snakemake' '.snakemake/*' '.nextflow' '.nextflow/*'
  'dask-worker-space' 'dask-worker-space/*' 'node_modules' 'node_modules/*'
  '*.pyc' '*.pyo' '*.tmp' '*.temp' '*.swp' '*.swo' '*~'
  '.DS_Store' 'Thumbs.db' '*.tgz' '*.tar.gz'
)

for pattern in "${extra_exclude_patterns[@]}"; do
  if [[ -z "$pattern" || "$pattern" == /* || "$pattern" == "Results" || "$pattern" != Results/* || "$pattern" == *'/../'* || "$pattern" == '../'* || "$pattern" == *'/..' ]]; then
    echo "ERROR: extra exclusion must be a non-empty project-relative path below Results/: $pattern" >&2
    exit 2
  fi
  exclude_patterns+=("$pattern" "*/$pattern")
done
echo "EXTRA_EXCLUDE_PATTERNS=${#extra_exclude_patterns[@]}"

tar_excludes=()
for pattern in "${exclude_patterns[@]}"; do
  tar_excludes+=("--exclude=$pattern")
done

cache_count=$(find "$source_project/Results" -type d \( \
  -name '__pycache__' -o -name '.cache' -o -name '.pytest_cache' -o \
  -name '.ruff_cache' -o -name '.mypy_cache' -o -name '.ipynb_checkpoints' -o \
  -name '.snakemake' -o -name '.nextflow' -o -name 'dask-worker-space' -o \
  -name 'node_modules' \) -print | wc -l)
echo "CACHE_DIRECTORIES_FOUND=$cache_count"
html_count=$(find "$source_project/Results" -type f \( -iname '*.html' -o -iname '*.htm' \) -print | wc -l)
echo "HTML_FILES_FOUND=$html_count"

temporary_archive=$(mktemp "$destination_dir/.${archive_basename}.tgz.tmp.XXXXXX")
temporary_tar=$(mktemp "$destination_dir/.${archive_basename}.tar.tmp.XXXXXX")
cleanup() {
  rm -f "$temporary_archive"
  rm -f "$temporary_tar"
}
trap cleanup EXIT

tar --ignore-case -C "$source_parent" -cf "$temporary_tar" "${tar_excludes[@]}" \
  "--exclude=$source_name/Results/Report_delivery" \
  "$source_name/Results"

report_source="$source_project/Results/Report_delivery"
report_source_present=0
if [[ -d "$report_source" ]]; then
  report_source_present=1
  if [[ ! -f "$report_source/Report.html" ]]; then
    echo "ERROR: Report_delivery exists but final Report.html is absent" >&2
    exit 7
  fi
  tar -C "$source_parent" -rf "$temporary_tar" \
    "$source_name/Results/Report_delivery/Report.html"
  if [[ -d "$report_source/Results" ]]; then
    tar --ignore-case -C "$source_parent" -rf "$temporary_tar" "${tar_excludes[@]}" \
      "$source_name/Results/Report_delivery/Results"
  fi
fi

pigz < "$temporary_tar" > "$temporary_archive"
audit_counts=$(python3 - "$temporary_archive" "$source_name" "$source_project" "${extra_exclude_patterns[@]}" <<'PY'
import fnmatch
from pathlib import Path
import re
import sys
import tarfile

general_pattern = re.compile(
    r"((^|/)data/raw(/|$)|manifest|\.h5ad(\.gz)?$|\.[rd][ds]$|\.rdata$|"
    r"report\.bundle_|report_assets|table_previews|preview_resources|(^|/)previews(/|$)|"
    r"figure_index\.tsv$|file_index\.tsv$|(^|/)index\.(tsv|csv)$|run_summary|\.map$|screenshots|review_build|draft|"
    r"\.log$|loom$|bam|arrow|gallery|\.h5$|save-uwot-umap.*tar$|impute-weights|"
    r"\.pkl(\.gz)?$|bgz$|\.qs2?$|\.mmd?$|\.docx?$|\.txt$|\.html?$|"
    r"(^|/)__pycache__(/|$)|(^|/)\.cache(/|$)|(^|/)\.pytest_cache(/|$)|"
    r"(^|/)\.ruff_cache(/|$)|(^|/)\.mypy_cache(/|$)|"
    r"(^|/)\.ipynb_checkpoints(/|$)|(^|/)\.snakemake(/|$)|"
    r"(^|/)\.nextflow(/|$)|(^|/)dask-worker-space(/|$)|"
    r"(^|/)node_modules(/|$)|\.py[co]$|\.(tmp|temp|swp|swo)$|~$|"
    r"(^|/)\.ds_store$|(^|/)thumbs\.db$|\.tgz$|\.tar\.gz$)",
    re.IGNORECASE,
)
entries = 0
excluded = 0
outside_results = 0
results_root = f"{sys.argv[2]}/Results"
user_exclude_matches = 0
user_excludes = sys.argv[4:]
report_members = set()
report_archive_files = set()
html_outside_report_matches = 0
with tarfile.open(sys.argv[1], mode="r:gz") as archive:
    for member in archive:
        entries += 1
        if member.name != results_root and not member.name.startswith(f"{results_root}/"):
            outside_results += 1
            if outside_results <= 50:
                print(f"OUTSIDE_RESULTS\t{member.name}", file=sys.stderr)
        project_relative = member.name.removeprefix(f"{sys.argv[2]}/")
        in_report_delivery = project_relative == "Results/Report_delivery" or project_relative.startswith("Results/Report_delivery/")
        if in_report_delivery:
            report_members.add(project_relative)
            if member.isfile() or member.issym() or member.islnk():
                report_archive_files.add(project_relative)
        if (not in_report_delivery) and re.search(r"\.html?$", member.name, re.IGNORECASE):
            html_outside_report_matches += 1
            if html_outside_report_matches <= 50:
                print(f"HTML_OUTSIDE_REPORT_MATCH\t{member.name}", file=sys.stderr)
        if any(fnmatch.fnmatchcase(project_relative, item) for item in user_excludes):
            user_exclude_matches += 1
            if user_exclude_matches <= 50:
                print(f"USER_EXCLUDE_MATCH\t{member.name}", file=sys.stderr)
        if project_relative != "Results/Report_delivery/Report.html" and general_pattern.search(member.name):
            excluded += 1
            if excluded <= 50:
                print(f"EXCLUDED_MATCH\t{member.name}", file=sys.stderr)
report_source_root = Path(sys.argv[3]) / "Results" / "Report_delivery"
report_source_files = set()
if report_source_root.is_dir():
    report_source_files.add("Results/Report_delivery/Report.html")
    copied_results = report_source_root / "Results"
    for item in copied_results.rglob("*"):
        if not (item.is_file() or item.is_symlink()):
            continue
        relative = "Results/Report_delivery/Results/" + item.relative_to(copied_results).as_posix()
        if general_pattern.search(relative) or any(fnmatch.fnmatchcase(relative, pattern) for pattern in user_excludes):
            continue
        report_source_files.add(relative)
        if item.suffix.lower() in {".png", ".pdf", ".svg", ".jpg", ".jpeg"}:
            original = Path(sys.argv[3]) / "Results" / item.relative_to(copied_results)
            if not original.is_file() or item.read_bytes() != original.read_bytes():
                raise SystemExit(f"ERROR: report figure is missing or differs from current Results: {relative}")
report_missing_files = sorted(report_source_files - report_archive_files)
for item in report_missing_files[:50]:
    print(f"REPORT_MISSING_FILE\t{item}", file=sys.stderr)
report_html = "Results/Report_delivery/Report.html" in report_members
report_md = "Results/Report_delivery/Report.md" in report_members
report_bundles = {
    item.split("/", 3)[2]
    for item in report_members
    if item.startswith("Results/Report_delivery/Report.bundle_")
}
if report_html:
    from html.parser import HTMLParser
    from urllib.parse import unquote, urlsplit
    import posixpath
    class ResourceParser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if key not in {"src", "href", "data-source-href", "data-table-path"} or not value:
                    continue
                parsed = urlsplit(value)
                if parsed.scheme or value.startswith("#"):
                    continue
                target = posixpath.normpath(posixpath.join("Results/Report_delivery", unquote(parsed.path)))
                if not target.startswith("Results/") or f"{sys.argv[2]}/{target}" not in archive_names:
                    raise SystemExit(f"ERROR: final HTML references an excluded or missing resource: {value}")
    with tarfile.open(sys.argv[1], mode="r:gz") as checked:
        archive_names = set(checked.getnames())
        html_bytes = checked.extractfile(f"{sys.argv[2]}/Results/Report_delivery/Report.html").read()
    ResourceParser().feed(html_bytes.decode("utf-8"))
report_complete = int(report_html and len(report_bundles) == 0 and not report_missing_files)
print(
    f"{entries}\t{excluded}\t{outside_results}\t{user_exclude_matches}\t"
    f"{len(report_members)}\t{report_complete}\t{len(report_bundles)}\t"
    f"{html_outside_report_matches}\t{len(report_source_files)}\t"
    f"{len(report_archive_files)}\t{len(report_missing_files)}\t{int(report_html)}"
)
PY
)
IFS=$'\t' read -r archive_entries excluded_matches outside_results_matches user_exclude_matches report_member_count report_complete report_bundle_count html_outside_report_matches report_source_files report_archive_files report_missing_files report_html_present <<< "$audit_counts"
echo "ARCHIVE_ENTRIES=$archive_entries"
echo "EXCLUDED_MATCHES=$excluded_matches"
echo "OUTSIDE_RESULTS_MATCHES=$outside_results_matches"
echo "USER_EXCLUDE_MATCHES=$user_exclude_matches"
echo "REPORT_SOURCE_PRESENT=$report_source_present"
echo "REPORT_ARCHIVE_ENTRIES=$report_member_count"
echo "REPORT_BUNDLE_DIRECTORIES=$report_bundle_count"
echo "REPORT_SOURCE_FILES=$report_source_files"
echo "REPORT_ARCHIVE_FILES=$report_archive_files"
echo "REPORT_MISSING_FILES=$report_missing_files"
echo "REPORT_HTML_PRESENT=$report_html_present"
echo "HTML_OUTSIDE_REPORT_MATCHES=$html_outside_report_matches"
if [[ "$html_outside_report_matches" -ne 0 ]]; then
  echo "ERROR: archive contains HTML entries outside Results/Report_delivery" >&2
  exit 8
fi
if [[ "$excluded_matches" -ne 0 ]]; then
  echo "ERROR: archive contains excluded entries" >&2
  exit 4
fi
if [[ "$outside_results_matches" -ne 0 ]]; then
  echo "ERROR: archive contains entries outside Results" >&2
  exit 5
fi
if [[ "$user_exclude_matches" -ne 0 ]]; then
  echo "ERROR: archive contains user-excluded entries" >&2
  exit 6
fi
if [[ "$report_source_present" -eq 1 && "$report_complete" -ne 1 ]]; then
  echo "ERROR: source contains Report_delivery but archive does not contain a complete final HTML report" >&2
  exit 7
fi
if [[ "$report_source_present" -eq 1 ]]; then
  echo "REPORT_PRESERVATION_STATUS=complete"
else
  echo "REPORT_PRESERVATION_STATUS=not_present"
fi

mv "$temporary_archive" "$archive_path"
sha256sum "$archive_path" > "$checksum_path"
chmod g+r "$archive_path" "$checksum_path"
rm -f "$temporary_tar"
trap - EXIT

echo "VALIDATION_OK"
echo "ARCHIVE=$archive_path"
echo "CHECKSUM=$checksum_path"
sha256sum "$archive_path"
