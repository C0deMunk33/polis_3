from tools.slop import SLOP
from libs.common import ToolCall
import os
import re
import subprocess
import tempfile
import sys



def extract_mermaid_from_markdown(markdown_file):
    """Extract mermaid diagram code from a markdown file."""
    with open(markdown_file, 'r') as f:
        content = f.read()
    
    # Find content between ```mermaid and ``` tags
    mermaid_pattern = r'```mermaid\n(.*?)```'
    match = re.search(mermaid_pattern, content, re.DOTALL)
    
    if match:
        return match.group(1)
    else:
        raise ValueError("No mermaid diagram found in the markdown file")

def render_mermaid_to_png(mermaid_code, output_file):
    """Render mermaid code to PNG using mmdc CLI with cyberpunk terminal theme."""
    # Check if mmdc is installed
    try:
        subprocess.run(['mmdc', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Mermaid CLI not found. Installing...")
        subprocess.run(['npm', 'install', '-g', '@mermaid-js/mermaid-cli'], check=True)
    
    # Create a temporary file for the mermaid code with cyberpunk styling
    cyberpunk_mermaid = f"""%%{{
  init: {{
    'theme': 'dark',
    'themeVariables': {{
      'primaryColor': '#ff00ff',
      'primaryTextColor': '#00ffff',
      'primaryBorderColor': '#ff00ff',
      'lineColor': '#00ffff',
      'secondaryColor': '#550055',
      'tertiaryColor': '#003333',
      'background': '#000000',
      'mainBkg': '#101020',
      'nodeBorder': '#ff00ff',
      'clusterBkg': '#220033',
      'clusterBorder': '#ff00ff',
      'titleColor': '#00ffff',
      'edgeLabelBackground': '#000000',
      'textColor': '#00ffff',
      'fontSize': '16px'
    }},
    'flowchart': {{
      'htmlLabels': true,
      'padding': 15,
      'nodeSpacing': 50,
      'rankSpacing': 80,
      'curve': 'basis'
    }}
  }}
}}%%

{mermaid_code}"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as temp:
        temp.write(cyberpunk_mermaid)
        temp_path = temp.name
    
    # Create a temporary CSS file for additional cyberpunk styling
    cyberpunk_css = """
    body { background-color: #000000; }
    .node rect, .node circle, .node ellipse, .node polygon, .node path {
        fill: #101020;
        stroke: #ff00ff;
        stroke-width: 2px;
    }
    .node .label {
        color: #00ffff;
        font-family: 'Courier New', monospace;
        font-size: 16px;
    }
    .edgePath .path {
        stroke: #00ffff;
        stroke-width: 2px;
    }
    .edgeLabel {
        background-color: transparent !important;
        color: #00ffff;
        font-family: 'Courier New', monospace;
        font-size: 16px;
    }
    .edgeLabel rect {
        fill: #000000 !important;
        opacity: 0.7 !important;
    }
    .cluster rect {
        fill: #220033;
        stroke: #ff00ff;
        stroke-width: 2px;
    }
    /* Fix for cut-off labels without halos */
    .label foreignObject {
        overflow: visible;
    }
    .edgeLabel foreignObject {
        overflow: visible;
    }
    /* Remove background from edge labels */
    .edgeLabel span {
        background-color: transparent !important;
    }
    /* Add a subtle glow effect to text */
    .node .label text, .edgeLabel text {
        text-shadow: 0 0 5px #00ffff;
    }
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.css', delete=False) as css_temp:
        css_temp.write(cyberpunk_css)
        css_path = css_temp.name
    
    try:
        # Run mmdc to generate the PNG with cyberpunk theme
        print(f"Running mmdc with input: {temp_path}, output: {output_file}")
        
        # Use full path for output file
        abs_output_path = os.path.abspath(output_file)
        print(f"Absolute output path: {abs_output_path}")
        
        # Updated command with cyberpunk theme parameters
        result = subprocess.run([
            'mmdc',
            '-i', temp_path,
            '-o', abs_output_path,
            '--backgroundColor', '#000000',
            '--width', '2048',
            '--height', '2048',
            '--cssFile', css_path,
            '--theme', 'dark',
            '--scale', '1.2'  # Slightly reduced scale to minimize halos
        ], check=True, capture_output=True, text=True)
        
        print(f"Command output: {result.stdout}")
        print(f"Command errors: {result.stderr}")
        
        # Verify the file was created
        if os.path.exists(abs_output_path):
            file_size = os.path.getsize(abs_output_path)
            print(f"Successfully rendered cyberpunk diagram to {abs_output_path} (Size: {file_size} bytes)")
        else:
            print(f"ERROR: Output file {abs_output_path} was not created!")
            
    except subprocess.CalledProcessError as e:
        print(f"Error running mmdc: {e}")
        print(f"Command output: {e.stdout}")
        print(f"Command errors: {e.stderr}")
        raise
    finally:
        # Clean up the temporary files
        os.unlink(temp_path)
        os.unlink(css_path)

def main():
    markdown_file = 'ecosystem_flow.md'
    output_file = 'ecosystem_flow.png'
    
    try:
        # Check if the markdown file exists
        if not os.path.exists(markdown_file):
            print(f"Error: Markdown file '{markdown_file}' not found")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Files in directory: {os.listdir('.')}")
            return
            
        # Extract mermaid code from markdown
        mermaid_code = extract_mermaid_from_markdown(markdown_file)
        print(f"Extracted mermaid code ({len(mermaid_code)} characters)")
        
        # Render to PNG
        render_mermaid_to_png(mermaid_code, output_file)
        
        # Final verification
        if os.path.exists(output_file):
            print(f"Verification: File exists at {output_file} with size {os.path.getsize(output_file)} bytes")
        else:
            print(f"Verification FAILED: File does not exist at {output_file}")
            
    except Exception as e:
        print(f"Error: {e}")
        
        # If extraction fails, provide alternative installation instructions
        print("\nAlternative method:")
        print("1. Install Mermaid CLI: npm install -g @mermaid-js/mermaid-cli")
        print("2. Copy the mermaid code from agent_flow.md to a file named diagram.mmd")
        print("3. Run: mmdc -i diagram.mmd -o agent_flow.png")

if __name__ == "__main__":
    main()