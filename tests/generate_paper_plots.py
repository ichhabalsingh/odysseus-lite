import os
import matplotlib.pyplot as plt
import numpy as np

# Apply professional style for academic publications
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'figure.titlesize': 14
})

# =====================================================================
# DATA FOR PLOTS
# =====================================================================
tasks = ['Task 1\n(Deps Summary)', 'Task 2\n(CORS Config)', 'Task 3\n(YOLO Path Compare)']
architectures = [
    'Single-Model ReAct (Baseline)',
    'Planner-Executor (DeepSeek 1.5B)',
    'Schema-Driven (Llama 8B)',
    'Schema-Driven + Compactor (Ours)'
]

colors = ['#e06c75', '#61afef', '#d19a66', '#98c379'] # One Dark inspired (Red, Blue, Orange, Green)

# Latency (seconds)
latency_data = {
    'Single-Model ReAct (Baseline)': [10.37, 13.32, 20.16],
    'Planner-Executor (DeepSeek 1.5B)': [73.49, 36.94, 40.97],
    'Schema-Driven (Llama 8B)': [69.09, 75.86, 138.89],
    'Schema-Driven + Compactor (Ours)': [42.52, 63.50, 59.46]
}

# Errors (count)
error_data = {
    'Single-Model ReAct (Baseline)': [4, 0, 5],
    'Planner-Executor (DeepSeek 1.5B)': [9, 2, 2],
    'Schema-Driven (Llama 8B)': [3, 4, 7],
    'Schema-Driven + Compactor (Ours)': [2, 2, 0]
}

# =====================================================================
# PLOT 1: LATENCY COMPARISON
# =====================================================================
def plot_latency():
    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = np.arange(len(tasks))
    width = 0.2
    
    for i, arch in enumerate(architectures):
        rects = ax.bar(x + (i - 1.5) * width, latency_data[arch], width, label=arch, color=colors[i], edgecolor='black', linewidth=0.5)
        # Add labels on top of the bars
        ax.bar_label(rects, padding=3, fmt='%.1fs', fontsize=8)
        
    ax.set_ylabel('Execution Time (seconds)')
    ax.set_title('Total Execution Latency Comparison (Lower is Better)')
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.legend(frameon=True, facecolor='white', edgecolor='lightgray')
    ax.set_ylim(0, 160)
    plt.tight_layout()
    
    output_path = os.path.join(os.path.dirname(__file__), 'benchmark_latency.png')
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"✓ Saved Latency Plot to: {output_path}")

# =====================================================================
# PLOT 2: ERROR COMPARISON
# =====================================================================
def plot_errors():
    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = np.arange(len(tasks))
    width = 0.2
    
    for i, arch in enumerate(architectures):
        rects = ax.bar(x + (i - 1.5) * width, error_data[arch], width, label=arch, color=colors[i], edgecolor='black', linewidth=0.5)
        ax.bar_label(rects, padding=3, fmt='%d', fontsize=8)
        
    ax.set_ylabel('Syntax & Parsing Errors')
    ax.set_title('Syntactic Loop & Omission Errors Comparison (Lower is Better)')
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.legend(frameon=True, facecolor='white', edgecolor='lightgray')
    ax.set_ylim(0, 11)
    plt.tight_layout()
    
    output_path = os.path.join(os.path.dirname(__file__), 'benchmark_errors.png')
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"✓ Saved Error Plot to: {output_path}")

# =====================================================================
# PLOT 3: ARCHITECTURE FLOWCHART
# =====================================================================
def draw_flowchart():
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axis('off')
    
    # Define box style
    box_props = dict(boxstyle='round,pad=0.5', facecolor='#2c384e', edgecolor='#61afef', lw=1.5)
    text_props = dict(color='white', ha='center', va='center', fontsize=9.5, fontweight='bold')
    
    # 1. User Goal
    ax.text(0.1, 0.8, 'User Goal\n(Request)', bbox=dict(boxstyle='round,pad=0.5', facecolor='#3e4451', edgecolor='#98c379', lw=1.5), **text_props)
    
    # 2. Schema-Driven Planner
    ax.text(0.4, 0.8, 'Schema-Driven Planner\n(Llama-3.1 8B)\nConstraint Mapping', bbox=box_props, **text_props)
    
    # 3. Step Plan JSON
    ax.text(0.75, 0.8, 'Plan Steps JSON\n[(tool_1, desc_1), ...]', bbox=dict(boxstyle='round,pad=0.5', facecolor='#282c34', edgecolor='#e5c07b', lw=1.5), **text_props)
    
    # 4. Executor Model
    ax.text(0.75, 0.5, 'Executor Model\n(Qwen-3B)\nGenerates Args Only', bbox=box_props, **text_props)
    
    # 5. Permission Gate
    ax.text(0.75, 0.2, 'Interactive Gateway\n(Thread Lock Event)', bbox=dict(boxstyle='round,pad=0.5', facecolor='#e06c75', edgecolor='red', lw=1.5), **text_props)
    
    # 6. Tool Execution
    ax.text(0.4, 0.2, 'Tool Execution\n(Local workspace / bash)', bbox=box_props, **text_props)
    
    # 7. State Compactor
    ax.text(0.1, 0.2, 'State Compactor\n(Observation Summarizer)', bbox=box_props, **text_props)
    
    # Draw arrows
    arrow_props = dict(arrowstyle="->", lw=1.5, color='#abb2bf', shrinkA=5, shrinkB=5)
    
    # Horizontal arrows (Top row)
    ax.annotate('', xy=(0.25, 0.8), xytext=(0.2, 0.8), arrowprops=arrow_props)
    ax.annotate('', xy=(0.6, 0.8), xytext=(0.55, 0.8), arrowprops=arrow_props)
    
    # Vertical arrow down (Right column)
    ax.annotate('', xy=(0.75, 0.6), xytext=(0.75, 0.7), arrowprops=arrow_props)
    ax.annotate('', xy=(0.75, 0.3), xytext=(0.75, 0.4), arrowprops=arrow_props)
    
    # Horizontal arrow left (Bottom row)
    ax.annotate('', xy=(0.58, 0.2), xytext=(0.63, 0.2), arrowprops=arrow_props)
    ax.annotate('', xy=(0.25, 0.2), xytext=(0.3, 0.2), arrowprops=arrow_props)
    
    # Vertical arrow up (Feedback loop)
    ax.annotate('Result Summary (Compact History)', xy=(0.1, 0.7), xytext=(0.1, 0.3), 
                arrowprops=dict(arrowstyle="->", lw=1.5, color='#98c379', shrinkA=5, shrinkB=5),
                ha='center', va='center', rotation=90, fontsize=8, color='#98c379', weight='bold')
    
    # Arrow from history summary to Executor
    ax.annotate('', xy=(0.63, 0.5), xytext=(0.1, 0.8), 
                arrowprops=dict(arrowstyle="->", lw=1.5, color='#98c379', connectionstyle="arc3,rad=-0.2"))

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    plt.tight_layout()
    
    output_path = os.path.join(os.path.dirname(__file__), 'architecture_flowchart.png')
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"✓ Saved Flowchart to: {output_path}")

if __name__ == '__main__':
    plot_latency()
    plot_errors()
    draw_flowchart()
