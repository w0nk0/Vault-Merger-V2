#!/usr/bin/env python3

"""
Gradio Web Interface for Obsidian Vault Merger
Provides a user-friendly web interface for merging and deduplicating Obsidian vaults.
"""

import gradio as gr
import os
import sys
from pathlib import Path
import subprocess
import json
from datetime import datetime
from typing import Tuple, Optional

# Custom CSS for beautiful styling
CUSTOM_CSS = """
/* Modern gradient background */
body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Container styling */
.main-container {
    background: white;
    border-radius: 15px;
    padding: 30px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
}

/* Header styling */
h1 {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.5em;
    font-weight: bold;
    margin-bottom: 20px;
}

/* Button styling */
.gr-button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important;
    padding: 15px 30px !important;
    border-radius: 25px !important;
    font-size: 16px !important;
    font-weight: bold !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
}

.gr-button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6) !important;
}

/* Input fields */
.gr-textbox, .gr-checkbox {
    border-radius: 10px !important;
    border: 2px solid #e0e0e0 !important;
    padding: 12px !important;
}

.gr-textbox:focus, .gr-checkbox:focus {
    border-color: #667eea !important;
    outline: none !important;
}

/* Output area */
.gr-textarea {
    border-radius: 10px !important;
    font-family: 'Courier New', monospace !important;
}

/* Card styling for sections */
.section-card {
    background: #f8f9fa;
    border-left: 4px solid #667eea;
    padding: 20px;
    margin: 20px 0;
    border-radius: 8px;
}

/* Status badges */
.status-success { background-color: #27ae60; color: white; padding: 5px 15px; border-radius: 20px; }
.status-error { background-color: #e74c3c; color: white; padding: 5px 15px; border-radius: 20px; }
.status-info { background-color: #3498db; color: white; padding: 5px 15px; border-radius: 20px; }
"""


def run_merge_command(source_paths: str, destination: str, deduplicate: bool, 
                     flatten: bool, analyze_only: bool, dedup_test: bool,
                     dedup_max_groups: int, no_rename: bool, delete_duplicates: bool) -> Tuple[str, Optional[str]]:
    """
    Execute the merge command and return output.
    
    Returns:
        Tuple of (status_message, report_path)
    """
    try:
        # Parse source paths
        sources = [p.strip() for p in source_paths.split('\n') if p.strip()]
        
        if not sources:
            return "❌ Error: At least one source path is required", None
        
        if analyze_only and len(sources) > 1:
            return "❌ Error: Analyze-only mode requires exactly one source path", None
        
        if not analyze_only and not destination:
            return "❌ Error: Destination path is required for merge mode", None
        
        # Build command
        cmd = [sys.executable, "main.py"] + sources
        
        if not analyze_only:
            cmd.extend(["-d", destination])
        
        if deduplicate:
            cmd.append("--deduplicate")
        
        if flatten:
            cmd.append("--flatten")
        
        if analyze_only:
            cmd.append("--analyze-only")
        
        if dedup_test:
            cmd.append("--dedup-test")
            cmd.extend(["--dedup-max-groups", str(dedup_max_groups)])
        
        if no_rename:
            cmd.append("--dedup-no-rename")
        
        if delete_duplicates:
            cmd.append("--dedup-delete")
        
        # Show command
        cmd_str = ' '.join(cmd)
        output = f"🚀 Running command:\n{cmd_str}\n\n"
        output += "=" * 60 + "\n"
        
        # Run the command
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        for line in process.stdout:
            output += line
        
        process.wait()
        
        # Check for report files
        if analyze_only:
            vault_path = sources[0]
        else:
            vault_path = destination
        
        report_path = os.path.join(vault_path, "deduplication_report.html")
        
        if process.returncode == 0:
            if deduplicate and os.path.exists(report_path):
                return f"✅ Process completed successfully!\n\n{output}\n\n📊 Report: {report_path}", report_path
            else:
                return f"✅ Process completed successfully!\n\n{output}", None
        else:
            return f"❌ Process failed with exit code {process.returncode}\n\n{output}", None
            
    except Exception as e:
        return f"❌ Error: {str(e)}", None


def create_web_interface():
    """Create and configure the Gradio web interface."""
    
    with gr.Blocks(css=CUSTOM_CSS, theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            """
            # 🔗 Obsidian Vault Merger
            
            Merge multiple Obsidian vaults and deduplicate files with identical content.
            
            ---
            """
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📂 Configuration")
                
                source_paths = gr.Textbox(
                    label="Source Vault Paths (one per line)",
                    placeholder="/path/to/vault1\n/path/to/vault2",
                    lines=3
                )
                
                # Directory picker for source paths (supports drag & drop)
                source_dir_upload = gr.File(
                    label="📎 Select Source Vaults - Drag & Drop Directories or Files",
                    file_count="multiple",
                    type="filepath",
                    interactive=True
                )
                
                destination = gr.Textbox(
                    label="Destination Vault Path",
                    placeholder="/path/to/merged_vault"
                )
                
                # Directory picker for destination (supports drag & drop)
                dest_dir_upload = gr.File(
                    label="📎 Select Destination Vault - Drag & Drop Directory",
                    file_count="single",
                    type="filepath",
                    interactive=True
                )
                
                gr.Markdown("### ⚙️ Options")
                
                deduplicate = gr.Checkbox(
                    label="Enable Deduplication",
                    value=False,
                    info="Remove duplicate files based on hash values"
                )
                
                flatten = gr.Checkbox(
                    label="Flatten Directory Structure",
                    value=False,
                    info="Don't preserve folder structure"
                )
                
                analyze_only = gr.Checkbox(
                    label="Analyze Only (No Merge)",
                    value=False,
                    info="Analyze existing vault without merging"
                )
        
            with gr.Column(scale=1):
                gr.Markdown("### 🔍 Deduplication Options")
                
                dedup_test = gr.Checkbox(
                    label="Test Mode (Safe)",
                    value=False,
                    info="Process only first few groups"
                )
                
                dedup_max_groups = gr.Slider(
                    label="Max Groups (Test Mode)",
                    minimum=1,
                    maximum=50,
                    value=3,
                    step=1
                )
                
                no_rename = gr.Checkbox(
                    label="Don't Rename Duplicates",
                    value=False,
                    info="Keep duplicates as-is (links still updated)"
                )
                
                delete_duplicates = gr.Checkbox(
                    label="Delete Duplicates After Relinking",
                    value=False,
                    info="Delete duplicate files instead of renaming them"
                )
        
        with gr.Row():
            export_config_btn = gr.Button("💾 Export Config", variant="secondary")
            import_config_btn = gr.File(
                label="Import Config",
                file_types=[".json"],
                type="filepath"
            )
        
        run_button = gr.Button("🚀 Run Merge/Deduplication", variant="primary", size="lg")
        
        gr.Markdown("---")
        
        with gr.Row():
            output_text = gr.Textbox(
                label="Output",
                lines=15,
                show_copy_button=True,
                interactive=False
            )
            
            report_view = gr.HTML(
                value="<p style='text-align: center; color: #7f8c8d;'>Report will appear here after deduplication</p>",
                label="📊 Deduplication Report"
            )
        
        def export_config(source_paths: str, destination: str, deduplicate: bool, 
                          flatten: bool, analyze_only: bool, dedup_test: bool,
                          dedup_max_groups: int, no_rename: bool, delete_duplicates: bool):
            """Export current configuration to JSON."""
            config = {
                "source_paths": source_paths,
                "destination": destination,
                "deduplicate": deduplicate,
                "flatten": flatten,
                "analyze_only": analyze_only,
                "dedup_test": dedup_test,
                "dedup_max_groups": dedup_max_groups,
                "no_rename": no_rename,
                "delete_duplicates": delete_duplicates
            }
            return json.dumps(config, indent=2)
        
        def import_config(file_path: str):
            """Import configuration from JSON file."""
            if file_path is None:
                return ""
            try:
                with open(file_path, 'r') as f:
                    config = json.load(f)
                return (
                    config.get("source_paths", ""),
                    config.get("destination", ""),
                    config.get("deduplicate", False),
                    config.get("flatten", False),
                    config.get("analyze_only", False),
                    config.get("dedup_test", False),
                    config.get("dedup_max_groups", 3),
                    config.get("no_rename", False),
                    config.get("delete_duplicates", False)
                )
            except Exception as e:
                return f"Error loading config: {e}"
        
        def run_and_display(source_paths: str, destination: str, deduplicate: bool, 
                           flatten: bool, analyze_only: bool, dedup_test: bool,
                           dedup_max_groups: int, no_rename: bool, delete_duplicates: bool):
            """Run command and display results including report."""
            status_message, report_path = run_merge_command(
                source_paths, destination, deduplicate, flatten, 
                analyze_only, dedup_test, dedup_max_groups, no_rename, delete_duplicates
            )
            
            # Load report HTML if it exists
            report_html = "<p style='text-align: center; color: #7f8c8d;'>No report generated</p>"
            if report_path and os.path.exists(report_path):
                try:
                    with open(report_path, 'r', encoding='utf-8') as f:
                        report_html = f.read()
                except Exception as e:
                    report_html = f"<p>Could not read report: {e}</p>"
            
            return status_message, report_html
        
        # Config export/import functionality
        def save_config_handler(source_paths: str, destination: str, deduplicate: bool, 
                                 flatten: bool, analyze_only: bool, dedup_test: bool,
                                 dedup_max_groups: int, no_rename: bool, delete_duplicates: bool):
            """Save config to file."""
            config = {
                "source_paths": source_paths,
                "destination": destination,
                "deduplicate": deduplicate,
                "flatten": flatten,
                "analyze_only": analyze_only,
                "dedup_test": dedup_test,
                "dedup_max_groups": dedup_max_groups,
                "no_rename": no_rename,
                "delete_duplicates": delete_duplicates
            }
            filename = f"obsidian_merger_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(os.getcwd(), filename)
            with open(filepath, 'w') as f:
                json.dump(config, f, indent=2)
            return filepath
        
        def load_config_handler(file_path):
            """Load config from file and return tuple of values for all inputs."""
            if file_path is None or not file_path:
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
            
            try:
                with open(file_path, 'r') as f:
                    config = json.load(f)
                return (
                    config.get("source_paths", ""),
                    config.get("destination", ""),
                    config.get("deduplicate", False),
                    config.get("flatten", False),
                    config.get("analyze_only", False),
                    config.get("dedup_test", False),
                    config.get("dedup_max_groups", 3),
                    config.get("no_rename", False),
                    config.get("delete_duplicates", False)
                )
            except Exception as e:
                return f"Error loading config: {e}", "", False, False, False, False, 3, False, False
        
        # Handle directory drag & drop for source paths
        def update_source_paths_from_drop(uploaded_files):
            """Extract full directory paths from dropped directories - NO FILE UPLOAD."""
            if uploaded_files is None or not uploaded_files:
                return gr.update()
            
            # Handle both single file and multiple files
            if isinstance(uploaded_files, str):
                uploaded_files = [uploaded_files]
            
            paths = []
            for file_path in uploaded_files:
                if os.path.exists(file_path):
                    # Always extract the directory path, never upload files
                    if os.path.isdir(file_path):
                        # It's a directory, use it directly
                        paths.append(file_path)
                    else:
                        # It's a file, use its parent directory
                        paths.append(os.path.dirname(file_path))
            
            # Return the concatenated paths as a new value for source_paths
            new_paths = "\n".join(paths)
            return gr.update(value=new_paths)
        
        # Handle directory drag & drop for destination
        def update_dest_from_drop(uploaded_file):
            """Extract full directory path from dropped directory - NO FILE UPLOAD."""
            if uploaded_file is None:
                return gr.update()
            
            dir_path = ""
            if os.path.exists(uploaded_file):
                if os.path.isdir(uploaded_file):
                    # It's a directory, use it directly
                    dir_path = uploaded_file
                else:
                    # It's a file, use its parent directory
                    dir_path = os.path.dirname(uploaded_file)
            
            return gr.update(value=dir_path)
        
        # Wire up directory drop handlers (capture paths only, no upload)
        source_dir_upload.upload(
            fn=update_source_paths_from_drop,
            inputs=[source_dir_upload],
            outputs=[source_paths]
        )
        
        dest_dir_upload.upload(
            fn=update_dest_from_drop,
            inputs=[dest_dir_upload],
            outputs=[destination]
        )
        
        # Wire up the buttons
        export_config_btn.click(
            fn=save_config_handler,
            inputs=[source_paths, destination, deduplicate, flatten, analyze_only, dedup_test, dedup_max_groups, no_rename, delete_duplicates],
            outputs=gr.File()
        )
        
        import_config_btn.upload(
            fn=load_config_handler,
            inputs=[import_config_btn],
            outputs=[source_paths, destination, deduplicate, flatten, analyze_only, dedup_test, dedup_max_groups, no_rename, delete_duplicates]
        )
        
        run_button.click(
            fn=run_and_display,
            inputs=[source_paths, destination, deduplicate, flatten, analyze_only, dedup_test, dedup_max_groups, no_rename, delete_duplicates],
            outputs=[output_text, report_view]
        )
    
    return demo


def main():
    """Launch the Gradio web interface."""
    demo = create_web_interface()
    demo.launch(
        server_name="0.0.0.0",  # Allow access from network
        server_port=7860,
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    main()

