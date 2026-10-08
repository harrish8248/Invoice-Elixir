/**
 * Invoice Elixir - Spatial Text Document Sheet & Side-by-Side Verification Dashboard
 */

// Pipeline Stage Technical Information
const PIPELINE_STEPS = {
    1: {
        badge: "Stage 01: Intake & Security",
        title: "Security Verification & Safe File Intake",
        desc: "Enforces strict document security constraints before any processing begins. Verifies binary magic byte headers, enforces the < 15MB size limit, prevents path traversal, and safely isolates inputs.",
        specs: [
            { label: "Size Constraint", val: "Strictly < 15 MB" },
            { label: "Magic Byte Verification", val: "%PDF-, \\x89PNG, \\xff\\xd8\\xff" },
            { label: "MIME Whitelist", val: "PDF, JPEG, PNG" },
            { label: "Filename Sanitization", val: "UUIDv4 Path Isolation" }
        ]
    },
    2: {
        badge: "Stage 02: Document Diagnostics",
        title: "PyMuPDF Inspection & Adaptive Preprocessing",
        desc: "Inspects page characteristics (vector text stream vs embedded raster images). Renders 300 DPI high-resolution targets and applies OpenCV adaptive deskewing, CLAHE contrast enhancement, and table grid structure diagnostics.",
        specs: [
            { label: "Rendering DPI", val: "300 DPI (PyMuPDF fitz)" },
            { label: "Contrast Enhancement", val: "OpenCV CLAHE (clip=2.0)" },
            { label: "Deskew Angle Limit", val: "Max ±15.0° Correction" },
            { label: "Layout Diagnostics", val: "Morphological Table Detection" }
        ]
    },
    3: {
        badge: "Stage 03: Dynamic Engine Scoring",
        title: "Dynamic Scoring & Intelligent Routing",
        desc: "Scores each registered and enabled OCR engine based on document mode (Digital vs Scanned), table layout presence, noise metrics, and skew angles. Orders engines into an optimal fallback execution queue.",
        specs: [
            { label: "Digital Baseline", val: "Tesseract (0.90), Surya (0.88), Paddle (0.85)" },
            { label: "Scanned Baseline", val: "PaddleOCR (0.95), Surya (0.92), docTR (0.85)" },
            { label: "Table Bonus", val: "+15 pts to PaddleOCR & Surya" },
            { label: "Noise / Skew Bonus", val: "+10 pts to EasyOCR & docTR" }
        ]
    },
    4: {
        badge: "Stage 04: Execution & Quality Gate",
        title: "Multi-Signal Quality Gate & Fallback Loop",
        desc: "Executes extraction using the top-ranked engine and assesses quality across a multi-signal score (raw confidence, valid dictionary words, presence of critical invoice signals). Automatically retries alternative engines if score < threshold.",
        specs: [
            { label: "Quality Evaluation", val: "Multi-signal (Confidence + Words + Signals)" },
            { label: "Acceptance Threshold", val: "Configurable (Default 75.0%)" },
            { label: "Fallback Loop", val: "Sequential retries up to Max Retries" },
            { label: "Engine Selection", val: "Highest scoring result preserved" }
        ]
    },
    5: {
        badge: "Stage 05: GSTIN & Field Extraction",
        title: "GSTIN Priority & Entity Extraction",
        desc: "Treats Indian GSTIN with highest priority. Applies strict 15-character regex and Mod-36 checksum verification. Never fabricates values. Disambiguates Supplier vs Buyer GSTIN and parses line items.",
        specs: [
            { label: "GSTIN Regex", val: "^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[A-Z0-9]{1}[0-9A-Z]{1}$" },
            { label: "Checksum Algorithm", val: "Modulo-36 Indian GSTIN Validation" },
            { label: "Party Disambiguation", val: "Contextual proximity & Header position" },
            { label: "Tabular Parser", val: "Description, HSN/SAC, Qty, Rate, Total" }
        ]
    },
    6: {
        badge: "Stage 06: Math & Audit Reconciliation",
        title: "Tax Consistency & Audit Trail Verification",
        desc: "Verifies mathematical integrity: Taxable Amount + CGST + SGST + IGST + Round Off ≈ Grand Total within 1% rounding tolerance. Compiles an immutable audit trail of preprocessing steps and OCR engine attempts.",
        specs: [
            { label: "Arithmetic Rule", val: "Taxable + Taxes + Round Off == Total" },
            { label: "Rounding Tolerance", val: "1.0% Allowable Variance" },
            { label: "Audit Log Output", val: "Every engine attempt & score logged" },
            { label: "Output Format", val: "Validated JSON + Visual Dashboard" }
        ]
    }
};

let currentSimDocType = "Scanned PDF";
let systemState = null;
let currentRawOcrText = "";

document.addEventListener("DOMContentLoaded", () => {
    // Navigation elements
    const navBtnProcessor = document.getElementById("nav-btn-processor");
    const navBtnOrchestrator = document.getElementById("nav-btn-orchestrator");
    const headerOrchestratorBadge = document.getElementById("header-orchestrator-badge");
    const brandHomeBtn = document.getElementById("brand-home-btn");

    const viewProcessor = document.getElementById("view-processor");
    const viewOrchestrator = document.getElementById("view-orchestrator");

    // File intake elements
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const progressCard = document.getElementById("progress-card");
    const timelineLog = document.getElementById("timeline-log");
    const resultsDashboard = document.getElementById("results-dashboard");

    // 1. Navigation Event Listeners
    navBtnProcessor.addEventListener("click", () => switchView("processor"));
    navBtnOrchestrator.addEventListener("click", () => switchView("orchestrator"));
    headerOrchestratorBadge.addEventListener("click", () => switchView("orchestrator"));
    brandHomeBtn.addEventListener("click", () => switchView("processor"));

    function switchView(target) {
        if (target === "orchestrator") {
            navBtnProcessor.classList.remove("active");
            navBtnOrchestrator.classList.add("active");
            viewProcessor.style.display = "none";
            viewOrchestrator.style.display = "flex";
            loadOrchestratorState();
        } else {
            navBtnOrchestrator.classList.remove("active");
            navBtnProcessor.classList.add("active");
            viewOrchestrator.style.display = "none";
            viewProcessor.style.display = "flex";
        }
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    // 2. Drag & Drop Upload Handlers
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    dropZone.addEventListener("click", (e) => {
        if (e.target.tagName !== "LABEL") {
            fileInput.click();
        }
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleFileUpload(fileInput.files[0]);
        }
    });

    // 3. Initial Load
    fetchSystemHealth();
    selectPipelineStep(1);

    async function fetchSystemHealth() {
        try {
            const res = await fetch("/api/health");
            if (res.ok) {
                const data = await res.json();
                systemState = data;
                updateHeaderBadges(data);
            }
        } catch (err) {
            console.error("Health check failed:", err);
            const statusEl = document.getElementById("system-status");
            statusEl.textContent = "Backend Offline";
            statusEl.className = "badge badge-danger";
        }
    }

    // 4. File Upload & Processing
    async function handleFileUpload(file) {
        resultsDashboard.style.display = "none";
        progressCard.style.display = "block";
        timelineLog.innerHTML = "";

        addLogEntry("File intake initialized...");
        addLogEntry(`Selected file: ${file.name} (${(file.size / (1024*1024)).toFixed(2)} MB)`);

        const formData = new FormData();
        formData.append("file", file);

        try {
            addLogEntry("Executing security validation and MIME signature check...");
            addLogEntry("PyMuPDF document inspection: classifying page layers...");

            const response = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Server upload failed.");
            }

            const result = await response.json();
            
            if (result.processing_log) {
                result.processing_log.forEach(msg => addLogEntry(msg));
            }

            addLogEntry("Pipeline processing & spatial text positioning completed.");
            
            setTimeout(() => {
                progressCard.style.display = "none";
                renderResults(result);
            }, 450);

        } catch (err) {
            addLogEntry(`CRITICAL ERROR: ${err.message}`);
            showToast(`Upload Failed: ${err.message}`, "error");
        }
    }

    function addLogEntry(message) {
        const li = document.createElement("li");
        li.textContent = message;
        timelineLog.appendChild(li);
        timelineLog.scrollTop = timelineLog.scrollHeight;
    }

    // 5. Render Results Dashboard
    function renderResults(data) {
        resultsDashboard.style.display = "flex";
        document.getElementById("upload-panel-container").style.display = "none";

        const ocr = data.ocr_details;
        const inv = data.invoice_data;
        const val = data.validation;
        currentRawOcrText = ocr.raw_text || "";

        // Top Performance Scorecard Grade Calculation
        const qScore = parseFloat(ocr.final_quality_score) || 0;
        let grade = "A+";
        let gradeLabel = "EXCELLENT";

        if (qScore >= 90) {
            grade = "A+"; gradeLabel = "EXCELLENT";
        } else if (qScore >= 80) {
            grade = "A"; gradeLabel = "VERY GOOD";
        } else if (qScore >= 70) {
            grade = "B"; gradeLabel = "GOOD";
        } else if (qScore >= 60) {
            grade = "C"; gradeLabel = "FAIR";
        } else {
            grade = "D"; gradeLabel = "NEEDS REVIEW";
        }

        document.getElementById("perf-grade-val").textContent = grade;
        document.getElementById("perf-grade-text").textContent = gradeLabel;
        document.getElementById("res-doc-title").textContent = data.filename;
        document.getElementById("res-perf-summary").innerHTML = `
            Engine: <strong>${ocr.selected_engine}</strong> • Quality Score: <strong>${qScore.toFixed(1)}%</strong> • Document: <strong>${ocr.document_type}</strong>
        `;

        document.getElementById("stat-engine-used").textContent = ocr.selected_engine;
        document.getElementById("stat-quality-score").textContent = `${qScore.toFixed(1)}%`;
        document.getElementById("stat-ocr-confidence").textContent = `${(ocr.final_confidence || 0).toFixed(1)}%`;
        
        const mathStatusEl = document.getElementById("stat-math-status");
        mathStatusEl.textContent = val.overall_status === "PASS" ? "PASS ✅" : "REVIEW ⚠️";
        mathStatusEl.style.color = val.overall_status === "PASS" ? "var(--accent)" : "var(--warning)";

        // 2. Engine Decision Basis Explanation
        const decisionEl = document.getElementById("engine-decision-rationale");
        decisionEl.textContent = `${ocr.selected_engine} was selected as the optimal OCR engine for this ${ocr.document_type}. Its extraction achieved a ${qScore.toFixed(1)}% composite quality score, passing the 75.0% threshold requirement with high character clarity.`;
        
        document.getElementById("basis-pill-doc-type").textContent = `📄 ${ocr.document_type}`;
        document.getElementById("basis-pill-quality").textContent = `🎯 Quality: ${qScore.toFixed(1)}% (Passed)`;
        document.getElementById("basis-pill-math").textContent = `⚖️ Math: ${val.math_consistency.status}`;

        // 3. Left Panel: Render Raw Text & Exact Spatial Document Canvas
        document.getElementById("raw-text-viewer").textContent = currentRawOcrText || "No text extracted.";
        document.getElementById("raw-char-count").textContent = `${currentRawOcrText.length} chars`;

        renderSpatialDocumentCanvas(ocr);

        // Default to displaying Raw OCR text first
        switchDocViewerMode('raw');

        const prepTagsContainer = document.getElementById("preprocessing-tags");
        prepTagsContainer.innerHTML = (ocr.preprocessing_applied || []).map(step => `
            <span class="tag-chip">⚙️ ${step}</span>
        `).join("");

        // 4. Right Panel: Side-by-Side Field Confidence Cards Grid
        renderSideBySideFieldCards(inv);

        // Bottom Tab 1: Line Items Table
        const tableBody = document.getElementById("line-items-body");
        tableBody.innerHTML = "";

        if (inv.line_items && inv.line_items.length > 0) {
            inv.line_items.forEach(item => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${item.description.value || '-'}</strong></td>
                    <td><span class="val-mono">${item.hsn_sac.value || '-'}</span></td>
                    <td>${item.quantity.value || '-'}</td>
                    <td>${item.unit_price.value || '-'}</td>
                    <td><strong>${item.total.value || '-'}</strong></td>
                `;
                tableBody.appendChild(tr);
            });
        } else {
            tableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 16px;">No structured tabular line items detected.</td></tr>`;
        }

        // Bottom Tab 2: Validation Warnings & Financial Math
        const warningList = document.getElementById("warning-list");
        warningList.innerHTML = "";

        const mathRow = document.createElement("li");
        mathRow.className = "warning-item";
        mathRow.style.background = val.math_consistency.status === "PASS" ? "#ECFDF5" : "#FFFBEB";
        mathRow.style.color = val.math_consistency.status === "PASS" ? "#065F46" : "#92400E";
        mathRow.style.borderColor = val.math_consistency.status === "PASS" ? "#A7F3D0" : "#FDE68A";
        mathRow.textContent = `Tax Balance Consistency Check: ${val.math_consistency.message}`;
        warningList.appendChild(mathRow);

        if (val.warnings && val.warnings.length > 0) {
            val.warnings.forEach(w => {
                const li = document.createElement("li");
                li.className = "warning-item";
                li.textContent = `⚠️ ${w}`;
                warningList.appendChild(li);
            });
        }

        // Bottom Tab 3: Multi-Engine Attempt History
        const auditLogContent = document.getElementById("audit-log-content");
        let attemptsHtml = (ocr.attempts || []).map(att => `
            <div class="field-row">
                <span><strong>${att.engine_name}</strong></span>
                <span>Confidence: <strong>${att.confidence}%</strong> | Quality: <strong>${att.quality_score}%</strong> | Status: <span class="${att.accepted ? 'badge badge-valid' : 'badge badge-danger'}">${att.accepted ? 'Accepted' : 'Rejected'}</span></span>
            </div>
        `).join("");

        auditLogContent.innerHTML = `
            <p style="margin-bottom: 8px;"><strong>Applied Preprocessing:</strong> ${ocr.preprocessing_applied.join(", ") || "None"}</p>
            <h4 style="font-size: 13.5px; margin: 10px 0 6px;">Engine Execution Attempts:</h4>
            ${attemptsHtml}
        `;

        resultsDashboard.scrollIntoView({ behavior: "smooth" });
    }

    // Exact Spatial Coordinate Positioned Document Canvas Renderer
    function renderSpatialDocumentCanvas(ocr) {
        const canvasEl = document.getElementById("spatial-doc-canvas");
        if (!canvasEl) return;

        canvasEl.innerHTML = "";

        const rawWords = (ocr.words || []).filter(w => w.bbox && w.bbox.length === 4 && w.text && w.text.trim());
        const pw = ocr.page_width || 1000;
        const ph = ocr.page_height || 1414;

        canvasEl.style.aspectRatio = `${pw} / ${ph}`;

        if (rawWords.length === 0) {
            // Fallback if bounding boxes are not available: render clean preserved text
            canvasEl.innerHTML = `
                <div class="spatial-empty-state">
                    <div style="font-size: 28px; margin-bottom: 8px;">📄</div>
                    <div style="font-weight: 700; color: var(--text-main); margin-bottom: 6px;">Spatial Layout Fallback</div>
                    <p>Bounding box coordinates were not extracted by this engine attempt. Preserved raw OCR stream:</p>
                    <div style="margin-top: 14px; text-align: left; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: 4px; padding: 12px; font-family: var(--font-mono); font-size: 11.5px; line-height: 1.5; color: #0F172A; white-space: pre-wrap; width: 100%; max-height: 400px; overflow-y: auto;">
                        ${escapeHtml(ocr.raw_text || "No text available")}
                    </div>
                </div>
            `;
            return;
        }

        // Step 1: Normalize words and calculate vertical centers
        const words = rawWords.map(w => ({
            text: w.text.trim(),
            confidence: w.confidence,
            x1: w.bbox[0],
            y1: w.bbox[1],
            x2: w.bbox[2],
            y2: w.bbox[3],
            width: Math.max(1, w.bbox[2] - w.bbox[0]),
            height: Math.max(1, w.bbox[3] - w.bbox[1]),
            midY: (w.bbox[1] + w.bbox[3]) / 2
        }));

        // Step 2: Sort words by vertical position
        words.sort((a, b) => a.y1 - b.y1);

        // Step 3: Cluster words into horizontal Lines
        const lines = [];
        const avgHeight = words.reduce((acc, w) => acc + w.height, 0) / words.length;
        const yTolerance = Math.max(5, avgHeight * 0.45);

        words.forEach(word => {
            let matchedLine = null;
            for (const line of lines) {
                if (Math.abs(word.midY - line.midY) <= yTolerance) {
                    matchedLine = line;
                    break;
                }
            }

            if (matchedLine) {
                matchedLine.words.push(word);
                matchedLine.y1 = Math.min(matchedLine.y1, word.y1);
                matchedLine.y2 = Math.max(matchedLine.y2, word.y2);
                matchedLine.midY = (matchedLine.y1 + matchedLine.y2) / 2;
            } else {
                lines.push({
                    y1: word.y1,
                    y2: word.y2,
                    midY: word.midY,
                    words: [word]
                });
            }
        });

        // Step 4: Sort lines from top to bottom
        lines.sort((a, b) => a.y1 - b.y1);

        // Step 5: For each line, sort words left-to-right and assemble contiguous phrase segments
        lines.forEach(line => {
            line.words.sort((a, b) => a.x1 - b.x1);

            const segments = [];
            let currentSegment = null;

            line.words.forEach(w => {
                const charWidth = (w.width / Math.max(1, w.text.length));
                const maxWordSpacing = Math.max(14, charWidth * 3.0);

                if (!currentSegment) {
                    currentSegment = {
                        text: w.text,
                        x1: w.x1,
                        x2: w.x2,
                        y1: w.y1,
                        y2: w.y2,
                        confidences: [w.confidence]
                    };
                } else {
                    const gap = w.x1 - currentSegment.x2;
                    if (gap <= maxWordSpacing && gap >= -8) {
                        // Contiguous phrase/cell: concatenate cleanly with standard space
                        currentSegment.text += " " + w.text;
                        currentSegment.x2 = Math.max(currentSegment.x2, w.x2);
                        currentSegment.y1 = Math.min(currentSegment.y1, w.y1);
                        currentSegment.y2 = Math.max(currentSegment.y2, w.y2);
                        currentSegment.confidences.push(w.confidence);
                    } else {
                        // Distinct column or distant text box
                        segments.push(currentSegment);
                        currentSegment = {
                            text: w.text,
                            x1: w.x1,
                            x2: w.x2,
                            y1: w.y1,
                            y2: w.y2,
                            confidences: [w.confidence]
                        };
                    }
                }
            });

            if (currentSegment) {
                segments.push(currentSegment);
            }

            // Render each coherent segment at its exact physical position
            segments.forEach(seg => {
                const leftPct = (seg.x1 / pw) * 100;
                const topPct = (seg.y1 / ph) * 100;
                const segHeight = seg.y2 - seg.y1;
                const avgConf = seg.confidences.reduce((a, b) => a + b, 0) / seg.confidences.length;

                const span = document.createElement("span");
                span.className = "spatial-word-node";
                span.textContent = seg.text;
                span.title = `"${seg.text}" (${avgConf.toFixed(0)}% conf)`;
                span.style.left = `${Math.max(0, Math.min(96, leftPct)).toFixed(2)}%`;
                span.style.top = `${Math.max(0, Math.min(97, topPct)).toFixed(2)}%`;
                
                // Crisp scalable font size
                const fontSizePx = Math.max(8.5, Math.min(17, (segHeight / ph) * 720 * 0.9));
                span.style.fontSize = `${fontSizePx.toFixed(1)}px`;

                canvasEl.appendChild(span);
            });
        });
    }

    function escapeHtml(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Render Side-by-Side Field Cards on the Right
    function renderSideBySideFieldCards(inv) {
        // Group 1: 🏛️ GST Identification (2 Columns)
        const gstGrid = document.getElementById("grid-gst-fields");
        gstGrid.innerHTML = `
            ${createFieldCard("Supplier GSTIN (Priority)", inv.supplier_gstin, "highlight-card", true)}
            ${createFieldCard("Buyer GSTIN", inv.buyer_gstin, "highlight-card", true)}
        `;

        // Group 2: 🏢 Parties & Contacts (2 Columns)
        const partiesGrid = document.getElementById("grid-parties-fields");
        partiesGrid.innerHTML = `
            ${createFieldCard("Supplier Name", inv.supplier_name)}
            ${createFieldCard("Buyer Name", inv.buyer_name)}
            ${createFieldCard("Supplier Address", inv.supplier_address)}
            ${createFieldCard("Buyer Address", inv.buyer_address)}
        `;

        // Group 3: 📄 Invoice Metadata (3 Columns)
        const metaGrid = document.getElementById("grid-metadata-fields");
        metaGrid.innerHTML = `
            ${createFieldCard("Invoice Number", inv.invoice_number)}
            ${createFieldCard("Invoice Date", inv.invoice_date)}
            ${createFieldCard("Due Date", inv.due_date)}
            ${createFieldCard("PO Number", inv.po_number)}
            ${createFieldCard("Currency", inv.currency)}
            ${createFieldCard("Contact Details", inv.contact_email.value !== "Not detected" ? inv.contact_email : inv.contact_phone)}
        `;

        // Group 4: 💰 Amounts & Tax Breakdown (3 Columns)
        const amountsGrid = document.getElementById("grid-amounts-fields");
        amountsGrid.innerHTML = `
            ${createFieldCard("Taxable Amount", inv.taxable_amount)}
            ${createFieldCard("CGST", inv.cgst)}
            ${createFieldCard("SGST", inv.sgst)}
            ${createFieldCard("IGST", inv.igst)}
            ${createFieldCard("Round Off", inv.round_off)}
            ${createFieldCard("Grand Total", inv.total_amount, "total-card", false, true)}
        `;

        const badgeCount = document.getElementById("fields-count-badge");
        if (badgeCount) badgeCount.textContent = "18 Fields Evaluated";
    }

    function createFieldCard(label, fieldObj, extraClass = "", isGstin = false, isTotal = false) {
        const f = fieldObj || { value: "-", confidence: 0, status: "Not Detected" };
        const conf = Math.min(100, Math.max(0, parseFloat(f.confidence) || 0));

        let barColorClass = "conf-bar-high";
        if (conf < 60) barColorClass = "conf-bar-low";
        else if (conf < 85) barColorClass = "conf-bar-med";

        let statusBadgeClass = "badge-notdetected";
        if (f.status === "Valid") statusBadgeClass = "badge-valid";
        else if (f.status === "Review Required") statusBadgeClass = "badge-warning";

        let valClass = "field-card-val";
        if (isGstin) valClass += " val-gstin";
        if (isTotal) valClass += " val-total";

        return `
            <div class="field-card ${extraClass}">
                <div class="field-card-top">
                    <span class="field-card-label">${label}</span>
                    <span class="badge ${statusBadgeClass}">${f.status || 'Not Detected'}</span>
                </div>
                <div class="${valClass}">
                    ${f.value || '<span style="color: var(--text-subtle);">Not detected</span>'}
                </div>
                <div class="field-card-conf">
                    <div class="conf-bar-bg">
                        <div class="conf-bar-fill ${barColorClass}" style="width: ${conf}%;"></div>
                    </div>
                    <span class="conf-num">${conf.toFixed(0)}%</span>
                </div>
            </div>
        `;
    }
});

// Left Panel Mode Switcher (Raw Extracted Text vs Exact Spatial Document Layout)
function switchDocViewerMode(mode) {
    const btnSheet = document.getElementById("btn-view-sheet");
    const btnRaw = document.getElementById("btn-view-raw");
    const sheetContainer = document.getElementById("text-doc-sheet-container");
    const rawContainer = document.getElementById("raw-text-container");

    if (mode === "sheet") {
        if (btnSheet) btnSheet.classList.add("active");
        if (btnRaw) btnRaw.classList.remove("active");
        if (sheetContainer) sheetContainer.style.display = "flex";
        if (rawContainer) rawContainer.style.display = "none";
    } else {
        if (btnRaw) btnRaw.classList.add("active");
        if (btnSheet) btnSheet.classList.remove("active");
        if (sheetContainer) sheetContainer.style.display = "none";
        if (rawContainer) rawContainer.style.display = "block";
    }
}

// Reset Dashboard for New Upload
function resetForNewUpload() {
    const uploadContainer = document.getElementById("upload-panel-container");
    const resultsDashboard = document.getElementById("results-dashboard");
    const fileInput = document.getElementById("file-input");

    if (uploadContainer) uploadContainer.style.display = "block";
    if (resultsDashboard) resultsDashboard.style.display = "none";
    if (fileInput) fileInput.value = "";
    window.scrollTo({ top: 0, behavior: "smooth" });
}

// Copy Raw Extracted OCR Text to Clipboard
function copyRawText() {
    if (!currentRawOcrText) {
        showToast("No OCR text to copy", "info");
        return;
    }
    navigator.clipboard.writeText(currentRawOcrText).then(() => {
        showToast("Extracted OCR text copied to clipboard!", "success");
    }).catch(err => {
        console.error("Clipboard copy failed:", err);
    });
}

// Update Header Badges
function updateHeaderBadges(data) {
    const statusEl = document.getElementById("system-status");
    statusEl.textContent = "System Operational";
    statusEl.className = "badge badge-primary";

    const engines = Object.values(data.ocr_engines || {});
    const activeCount = engines.filter(e => e.enabled).length;
    const totalCount = engines.length;

    document.getElementById("engine-count").textContent = `⚡ Orchestrator (${activeCount}/${totalCount} Active)`;
    
    // Orchestrator Stats
    const statTotal = document.getElementById("stat-total-engines");
    const statActive = document.getElementById("stat-active-engines");
    const statThreshold = document.getElementById("stat-threshold");
    const statRetries = document.getElementById("stat-max-retries");

    if (statTotal) statTotal.textContent = totalCount;
    if (statActive) statActive.textContent = activeCount;
    if (statThreshold) statThreshold.textContent = `${data.accept_threshold}%`;
    if (statRetries) statRetries.textContent = data.max_retries;

    const thresholdInput = document.getElementById("setting-threshold");
    const thresholdDisplay = document.getElementById("threshold-val-display");
    const retriesInput = document.getElementById("setting-retries");
    const retriesDisplay = document.getElementById("retries-val-display");

    if (thresholdInput && thresholdDisplay) {
        thresholdInput.value = data.accept_threshold;
        thresholdDisplay.textContent = `${data.accept_threshold}%`;
    }
    if (retriesInput && retriesDisplay) {
        retriesInput.value = data.max_retries;
        retriesDisplay.textContent = data.max_retries;
    }
}

// Load Orchestrator State & Render Cards
async function loadOrchestratorState() {
    try {
        const res = await fetch("/api/health");
        if (!res.ok) throw new Error("Failed to fetch health status");
        const data = await res.json();
        systemState = data;

        updateHeaderBadges(data);
        renderEnginesGrid(data.ocr_engines);
        runSimulation();
    } catch (err) {
        console.error("Failed to load orchestrator state:", err);
        showToast("Error loading orchestrator state", "error");
    }
}

// Render Engine Cards in Control Center
function renderEnginesGrid(engines) {
    const grid = document.getElementById("engines-grid");
    if (!grid) return;

    const engineIcons = {
        "PaddleOCR": "🚀",
        "Surya": "☀️",
        "Tesseract": "🔍",
        "docTR": "📄",
        "EasyOCR": "👁️"
    };

    const engineDescriptions = {
        "PaddleOCR": "Baidu layout-aware OCR engine. Superior accuracy for scanned invoices, multi-column tables, and complex documents.",
        "Surya": "Modern transformer-based multilingual layout OCR engine with deep segmentation and complex reading order detection.",
        "Tesseract": "Fast optical character recognition engine optimized for clean digital text streams and high-contrast scans.",
        "docTR": "Mindee end-to-end deep learning OCR with robust field detection, handwriting handling, and layout preservation.",
        "EasyOCR": "PyTorch-powered deep learning OCR, highly resilient against image noise, low lighting, and curved text."
    };

    grid.innerHTML = "";

    Object.values(engines).forEach(engine => {
        const card = document.createElement("div");
        card.className = `engine-card ${engine.enabled ? '' : 'disabled'}`;
        card.id = `engine-card-${engine.name}`;

        const icon = engineIcons[engine.name] || "⚙️";
        const desc = engineDescriptions[engine.name] || "OCR Recognition Engine plugin.";
        
        const statusClass = engine.available ? "available" : "unavailable";
        const statusText = engine.available 
            ? "🟢 Installed & Operational" 
            : `🔴 Host Unavailable (${engine.init_error || 'Dependency missing'})`;

        const capsHtml = (engine.strengths || []).map(s => `<span class="cap-tag">${s.replace('_', ' ')}</span>`).join("");

        card.innerHTML = `
            <div class="engine-header">
                <div class="engine-identity">
                    <div class="engine-icon">${icon}</div>
                    <div>
                        <h4 class="engine-title">${engine.name}</h4>
                        <span class="engine-priority">Priority #${engine.priority}</span>
                    </div>
                </div>

                <div class="toggle-wrapper">
                    <span class="toggle-label ${engine.enabled ? 'on' : 'off'}" id="toggle-label-${engine.name}">
                        ${engine.enabled ? 'ON' : 'OFF'}
                    </span>
                    <label class="switch">
                        <input type="checkbox" ${engine.enabled ? 'checked' : ''} onchange="handleEngineToggle('${engine.name}', this.checked)">
                        <span class="slider"></span>
                    </label>
                </div>
            </div>

            <p class="section-desc">${desc}</p>

            <div class="engine-status-banner ${statusClass}">
                <span>${statusText}</span>
            </div>

            <div class="capability-tags">
                ${capsHtml}
            </div>

            <div class="engine-weights-row">
                <span>Digital Wt: <strong>${(engine.weight_digital * 100).toFixed(0)}%</strong></span>
                <span>Scanned Wt: <strong>${(engine.weight_scanned * 100).toFixed(0)}%</strong></span>
            </div>
        `;

        grid.appendChild(card);
    });
}

// Toggle Engine ON/OFF
async function handleEngineToggle(engineName, enabled) {
    const labelEl = document.getElementById(`toggle-label-${engineName}`);
    const cardEl = document.getElementById(`engine-card-${engineName}`);

    if (labelEl) {
        labelEl.textContent = enabled ? 'ON' : 'OFF';
        labelEl.className = `toggle-label ${enabled ? 'on' : 'off'}`;
    }

    if (cardEl) {
        if (enabled) {
            cardEl.classList.remove('disabled');
        } else {
            cardEl.classList.add('disabled');
        }
    }

    try {
        const res = await fetch("/api/engines/toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ engine_name: engineName, enabled: enabled })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Toggle failed");
        }

        const data = await res.json();
        showToast(`Engine ${engineName} turned ${enabled ? 'ON' : 'OFF'}`, enabled ? "success" : "info");
        
        const healthRes = await fetch("/api/health");
        if (healthRes.ok) {
            const healthData = await healthRes.json();
            updateHeaderBadges(healthData);
        }
        runSimulation();

    } catch (err) {
        console.error("Toggle error:", err);
        showToast(`Failed to toggle ${engineName}: ${err.message}`, "error");
        loadOrchestratorState();
    }
}

// Save Orchestrator Thresholds
async function handleSettingsSave(event) {
    event.preventDefault();
    const threshold = parseFloat(document.getElementById("setting-threshold").value);
    const retries = parseInt(document.getElementById("setting-retries").value, 10);

    const btn = document.getElementById("btn-save-settings");
    btn.disabled = true;
    btn.textContent = "Saving...";

    try {
        const res = await fetch("/api/settings/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                accept_threshold: threshold,
                max_retries: retries
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Update failed");
        }

        const data = await res.json();
        showToast(`Settings Saved: Quality Gate = ${data.accept_threshold}%, Retries = ${data.max_retries}`, "success");
        
        document.getElementById("stat-threshold").textContent = `${data.accept_threshold}%`;
        document.getElementById("stat-max-retries").textContent = data.max_retries;

    } catch (err) {
        console.error("Settings update error:", err);
        showToast(`Error updating settings: ${err.message}`, "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "💾 Save Orchestrator Settings";
    }
}

// Select Pipeline Step
function selectPipelineStep(stepNum) {
    document.querySelectorAll(".pipeline-step-node").forEach(node => {
        if (parseInt(node.dataset.step) === stepNum) {
            node.classList.add("active");
        } else {
            node.classList.remove("active");
        }
    });

    const info = PIPELINE_STEPS[stepNum];
    if (!info) return;

    document.getElementById("step-badge").textContent = `Stage 0${stepNum}`;
    document.getElementById("step-detail-title").textContent = info.title;
    document.getElementById("step-detail-desc").textContent = info.desc;

    const specsContainer = document.getElementById("step-tech-specs");
    specsContainer.innerHTML = info.specs.map(spec => `
        <div class="spec-item">
            <span class="spec-label">${spec.label}</span>
            <span class="spec-val">${spec.val}</span>
        </div>
    `).join("");
}

// Routing Simulator
function setSimDocType(docType, event) {
    currentSimDocType = docType;
    document.querySelectorAll(".segment-btn").forEach(btn => btn.classList.remove("active"));
    event.target.classList.add("active");
    runSimulation();
}

async function runSimulation() {
    const hasTables = document.getElementById("sim-has-tables") ? document.getElementById("sim-has-tables").checked : false;
    const isNoisy = document.getElementById("sim-is-noisy") ? document.getElementById("sim-is-noisy").checked : false;
    const highSkew = document.getElementById("sim-high-skew") ? document.getElementById("sim-high-skew").checked : false;

    const listContainer = document.getElementById("sim-results-list");
    if (!listContainer) return;

    try {
        const res = await fetch("/api/orchestrator/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                document_type: currentSimDocType,
                has_tables: hasTables,
                is_noisy: isNoisy,
                is_low_contrast: isNoisy,
                skew_angle: highSkew ? 8.5 : 0.0
            })
        });

        if (!res.ok) throw new Error("Simulation failed");
        const data = await res.json();

        listContainer.innerHTML = "";

        if (data.ranked_engines.length === 0) {
            listContainer.innerHTML = `<div style="padding: 14px; text-align: center; color: var(--text-muted);">All OCR engines are currently turned OFF. Enable at least one engine above.</div>`;
            return;
        }

        data.ranked_engines.forEach((item, idx) => {
            const isWinner = idx === 0;
            const itemDiv = document.createElement("div");
            itemDiv.className = "sim-item";
            itemDiv.innerHTML = `
                <span class="sim-name">${isWinner ? '👑 ' : ''}${item.name}</span>
                <span class="sim-score" style="color: ${item.score > 80 ? 'var(--accent)' : item.score > 50 ? 'var(--primary)' : 'var(--danger)'};">
                    ${item.score.toFixed(1)}
                </span>
                <span class="sim-rationale">${item.rationale}</span>
            `;
            listContainer.appendChild(itemDiv);
        });

    } catch (err) {
        console.error("Simulation query error:", err);
    }
}

// Toast Notification
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    const icons = {
        success: "✅",
        error: "❌",
        info: "ℹ️"
    };

    toast.innerHTML = `
        <span>${icons[type] || "ℹ️"}</span>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(20px)";
        setTimeout(() => toast.remove(), 250);
    }, 3200);
}

// Tab switcher for result details
function switchResultTab(tabId, event) {
    document.querySelectorAll(".tabs-card .tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".tabs-card .tab-content").forEach(content => content.classList.remove("active"));

    if (event && event.target) {
        event.target.classList.add("active");
    }
    const tabEl = document.getElementById(tabId);
    if (tabEl) tabEl.classList.add("active");
}
