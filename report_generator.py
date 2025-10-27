import os
from datetime import datetime
from typing import List, Dict
from config_manager import config_manager
from file_scanner import file_scanner
from collision_resolver import collision_resolver
from file_copier import file_copier
from link_processor import link_processor
from logger import logger


class ReportGenerator:
    """
    Generates comprehensive reports for the Obsidian Vault Merger tool.
    Creates HTML log files, link mapping files, and error reports.
    """

    def __init__(self):
        self.report_dir = os.path.join(config_manager.destination_path, ".merge_reports")
        os.makedirs(self.report_dir, exist_ok=True)

    def generate_merge_report(self) -> None:
        """
        Generate a comprehensive merge report including statistics and logs.
        """
        logger.info("Generating merge report...")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Generate HTML report
        html_report_path = os.path.join(self.report_dir, "merge_report.html")
        self._generate_html_report(html_report_path, timestamp)
        
        # Generate link mapping file
        link_processor.generate_link_mapping_file()
        
        # Generate rename log file
        self._generate_rename_log_file()
        
        logger.info(f"Merge report generated at {html_report_path}")

    def _generate_html_report(self, report_path: str, timestamp: str) -> None:
        """
        Generate an HTML report with merge statistics and logs.
        
        Args:
            report_path: Path where the HTML report should be saved
            timestamp: Timestamp of the merge operation
        """
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("<!DOCTYPE html>\n")
                f.write("<html>\n<head>\n")
                f.write("<title>Obsidian Vault Merge Report</title>\n")
                f.write("<style>\n")
                f.write("body { font-family: Arial, sans-serif; margin: 20px; }\n")
                f.write("h1, h2 { color: #333; }\n")
                f.write("table { border-collapse: collapse; width: 100%; }\n")
                f.write("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }\n")
                f.write("th { background-color: #f2f2f2; }\n")
                f.write(".stats { background-color: #f9f9f9; padding: 15px; border-radius: 5px; }\n")
                f.write("</style>\n")
                f.write("</head>\n<body>\n")
                
                f.write("<h1>Obsidian Vault Merge Report</h1>\n")
                f.write(f"<p>Generated on: {timestamp}</p>\n")
                
                # Configuration summary
                f.write("<h2>Configuration</h2>\n")
                f.write("<div class='stats'>\n")
                f.write(f"<p><strong>Source paths:</strong> {', '.join(config_manager.source_paths)}</p>\n")
                f.write(f"<p><strong>Destination path:</strong> {config_manager.destination_path}</p>\n")
                f.write(f"<p><strong>File types:</strong> {', '.join(config_manager.file_types)}</p>\n")
                f.write(f"<p><strong>Preserve folder structure:</strong> {config_manager.preserve_folder_structure}</p>\n")
                f.write(f"<p><strong>Exclude dot folders:</strong> {config_manager.exclude_dot_folders}</p>\n")
                f.write("</div>\n")
                
                # Statistics
                f.write("<h2>Statistics</h2>\n")
                f.write("<div class='stats'>\n")
                f.write(f"<p><strong>Total files processed:</strong> {len(file_scanner.get_file_inventory())}</p>\n")
                f.write(f"<p><strong>Files with collisions:</strong> {len(collision_resolver.get_resolved_files()) - len(file_scanner.get_file_inventory()) + len(collision_resolver.get_collision_candidates())}</p>\n")
                f.write(f"<p><strong>Files renamed:</strong> {collision_resolver.get_renamed_files_count()}</p>\n")
                f.write(f"<p><strong>Links processed:</strong> {len(link_processor.get_link_mapping())}</p>\n")
                f.write(f"<p><strong>Files copied:</strong> {len(file_copier.get_copy_log())}</p>\n")
                f.write("</div>\n")
                
                # Renamed files table
                renamed_files = file_copier.get_renamed_files_log()
                if renamed_files:
                    f.write("<h2>Renamed Files</h2>\n")
                    f.write("<table>\n")
                    f.write("<tr><th>Original Filename</th><th>New Filename</th><th>Source Path</th></tr>\n")
                    for entry in renamed_files:
                        f.write(f"<tr><td>{entry['original_filename']}</td>")
                        f.write(f"<td>{entry['resolved_filename']}</td>")
                        f.write(f"<td>{entry['source_path']}</td></tr>\n")
                    f.write("</table>\n")
                
                # Link mapping
                link_mapping = link_processor.get_link_mapping()
                if link_mapping:
                    f.write("<h2>Link Mapping</h2>\n")
                    f.write("<table>\n")
                    f.write("<tr><th>Target File</th><th>Source File</th><th>Link Type</th></tr>\n")
                    for mapping in link_mapping:
                        # Parse mapping string (format: "target <- source (type)")
                        parts = mapping.split(" <- ")
                        if len(parts) >= 2:
                            target = parts[0]
                            source_and_type = parts[1]
                            source_parts = source_and_type.split(" (")
                            source = source_parts[0] if source_parts else "unknown"
                            link_type = source_parts[1].rstrip(")") if len(source_parts) > 1 else "unknown"
                            f.write(f"<tr><td>{target}</td><td>{source}</td><td>{link_type}</td></tr>\n")
                    f.write("</table>\n")
                
                # Unresolved links
                unresolved_links = link_processor.get_unresolved_links()
                if unresolved_links:
                    f.write("<h2>Unresolved Links</h2>\n")
                    f.write("<ul>\n")
                    for link in unresolved_links:
                        f.write(f"<li>{link}</li>\n")
                    f.write("</ul>\n")
                
                f.write("</body>\n</html>\n")
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")

    def _generate_rename_log_file(self) -> None:
        """
        Generate a simple text file with rename mappings.
        """
        rename_log_path = os.path.join(self.report_dir, "rename_log.txt")
        try:
            with open(rename_log_path, 'w', encoding='utf-8') as f:
                f.write("# File Rename Log\n")
                f.write("# Format: original_filename -> new_filename\n\n")
                rename_log = collision_resolver.get_rename_log()
                for original, new in rename_log.items():
                    f.write(f"{original} -> {new}\n")
            logger.info(f"Rename log generated at {rename_log_path}")
        except Exception as e:
            logger.error(f"Failed to generate rename log: {e}")


# Global report generator instance
report_generator = ReportGenerator()