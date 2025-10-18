import pandas as pd

def format_response_as_html(text: str) -> str:
    """Convert plain text to HTML with basic formatting"""
    
    if not text:
        return ""
    
    lines = text.strip().split('\n')
    html_parts = []
    in_list = False
    list_type = None
    
    for line in lines:
        line = line.strip()
        
        if not line:
            if in_list:
                html_parts.append(f'</{list_type}>')
                in_list = False
                list_type = None
            continue
        
        # Handle bullet points
        if line.startswith(('- ', '* ', '• ')):
            if not in_list:
                html_parts.append('<ul>')
                in_list = True
                list_type = 'ul'
            elif list_type != 'ul':
                html_parts.append(f'</{list_type}>')
                html_parts.append('<ul>')
                list_type = 'ul'
            content = line[2:].strip()
            html_parts.append(f'<li>{content}</li>')
        
        # Handle numbered lists
        elif line[0].isdigit() and '. ' in line[:4]:
            if not in_list:
                html_parts.append('<ol>')
                in_list = True
                list_type = 'ol'
            elif list_type != 'ol':
                html_parts.append(f'</{list_type}>')
                html_parts.append('<ol>')
                list_type = 'ol'
            content = line.split('. ', 1)[1].strip()
            html_parts.append(f'<li>{content}</li>')
        
        # Regular paragraph
        else:
            if in_list:
                html_parts.append(f'</{list_type}>')
                in_list = False
                list_type = None
            html_parts.append(f'<p>{line}</p>')
    
    # Close any open list
    if in_list:
        html_parts.append(f'</{list_type}>')
    
    return '\n'.join(html_parts)

def dataframe_to_html(df: pd.DataFrame) -> str:
    """Convert dataframe to styled HTML table"""
    
    if df.empty:
        return "<p>No results found</p>"
    
    # Sort by score if available
    if "score" in df.columns:
        df = df.astype({"score": float}).sort_values("score", ascending=False)
    
    html = """
    <div style="overflow-x: auto; font-family: Arial, sans-serif;">
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background-color: #f8f9fa;">
    """
    
    # Table headers
    for col in df.columns:
        html += f'<th style="padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6; font-weight: 600;">{col}</th>'
    
    html += """
                </tr>
            </thead>
            <tbody>
    """
    
    # Table rows
    for idx, row in df.iterrows():
        html += '<tr style="border-bottom: 1px solid #dee2e6;">'
        
        for col in df.columns:
            value = row[col]
            
            # Format score with color
            if col == "score":
                try:
                    score_val = float(value)
                    if score_val >= 80:
                        color = "#10b981"
                    elif score_val >= 60:
                        color = "#f59e0b"
                    else:
                        color = "#ef4444"
                    html += f'<td style="padding: 12px; color: {color}; font-weight: 600;">{score_val:.1f}</td>'
                except:
                    html += f'<td style="padding: 12px;">{value}</td>'
            else:
                html += f'<td style="padding: 12px;">{value}</td>'
        
        html += '</tr>'
    
    html += """
            </tbody>
        </table>
    </div>
    """
    
    return html