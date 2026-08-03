#!/usr/bin/env python3
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_pdf(filename):
    print(f"Creating valid PDF: {filename}...")
    c = canvas.Canvas(filename, pagesize=letter)
    
    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 720, "Odysseus Lite Project Status Report")
    
    c.setFont("Helvetica", 10)
    c.drawString(72, 700, "Date: August 3, 2026 | Domain: Engineering & AI Agents")
    
    # Section 1: Executive Summary
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, 660, "1. Executive Summary")
    
    c.setFont("Helvetica", 10)
    text_lines = [
        "This project evaluates the performance and usability of Odysseus Lite, a secure,",
        "offline AI workspace co-pilot designed for local terminal execution.",
        "The system has been configured with strict execution boundaries, including",
        "interactive terminal permission gates (y/n confirmations) and RAG grounding."
    ]
    y = 640
    for line in text_lines:
        c.drawString(72, y, line)
        y -= 15
        
    # Section 2: Performance Metrics
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, y - 10, "2. Key Metrics & Benchmarks")
    y -= 30
    
    metrics = [
        "Metric A: Local RAG Search Latency - 0.25 milliseconds",
        "Metric B: Average 3B Model Execution Speed - 57.4 tokens/second",
        "Metric C: Task Synthesis Success Rate - 86.7 percent",
        "Metric D: Average Cycle Loop Time - 4.32 seconds"
    ]
    for m in metrics:
        c.drawString(72, y, m)
        y -= 15
        
    # Page Save
    c.showPage()
    c.save()
    print("✓ PDF written successfully!")

if __name__ == "__main__":
    create_pdf("report.pdf")
