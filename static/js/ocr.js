/**
 * Sulit Store Computer Vision OCR Expiration Scanner Controller
 * Implements Section 7 Step 2 & Section 4.2
 * Features:
 *   1. Real-time Webcam video scanner with target bounding guide
 *   2. File upload with OpenCV pre-processing filter previews (Grayscale, Thresholding)
 *   3. ISO 8601 date extraction & auto-injection into product forms
 *   4. Instant evaluation & synthetic retail packaging test cases
 */

const OCRScanner = {
    stream: null,
    targetInputId: "prod-form-expiry"
};

document.addEventListener("DOMContentLoaded", () => {
    initOCREvents();
});

function initOCREvents() {
    const fileInput = document.getElementById("ocr-file-upload");
    if (fileInput) {
        fileInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (file) {
                processUploadedImage(file);
            }
        });
    }
}

function openOCRModal(targetInputId = "prod-form-expiry") {
    OCRScanner.targetInputId = targetInputId;
    const modal = document.getElementById("ocr-scanner-modal");
    if (modal) modal.classList.add("active");

    // Clear previous results
    document.getElementById("ocr-detected-date-display").textContent = "Awaiting scan...";
    document.getElementById("ocr-filter-previews").style.display = "none";
    document.getElementById("ocr-results-box").style.display = "none";
}

function closeOCRModal() {
    stopCamera();
    const modal = document.getElementById("ocr-scanner-modal");
    if (modal) modal.classList.remove("active");
}

async function startCamera() {
    const video = document.getElementById("ocr-video-feed");
    const placeholder = document.getElementById("ocr-camera-placeholder");

    try {
        OCRScanner.stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } }
        });
        video.srcObject = OCRScanner.stream;
        video.style.display = "block";
        if (placeholder) placeholder.style.display = "none";
        showToast("Camera stream connected!", "info");
    } catch (err) {
        console.warn("Webcam access error / fallback to mock:", err);
        showToast("Webcam unavailable. You can use image upload or quick samples.", "warning");
    }
}

function stopCamera() {
    if (OCRScanner.stream) {
        OCRScanner.stream.getTracks().forEach(track => track.stop());
        OCRScanner.stream = null;
    }
    const video = document.getElementById("ocr-video-feed");
    if (video) video.style.display = "none";
    const placeholder = document.getElementById("ocr-camera-placeholder");
    if (placeholder) placeholder.style.display = "flex";
}

function captureVideoFrame() {
    const video = document.getElementById("ocr-video-feed");
    if (!video || !OCRScanner.stream) {
        showToast("Please start camera first or upload an image", "warning");
        return;
    }

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(blob => {
        const file = new File([blob], "camera_capture.png", { type: "image/png" });
        processUploadedImage(file);
    }, "image/png");
}

async function processUploadedImage(file) {
    const statusEl = document.getElementById("ocr-status-message");
    if (statusEl) statusEl.textContent = "Processing image through OpenCV pipeline...";

    const formData = new FormData();
    formData.append("image", file);

    try {
        const res = await fetch("/api/ocr/scan_image", {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        if (data.success) {
            // Render OpenCV Computer Vision filter previews
            if (data.filter_previews) {
                const previewsBox = document.getElementById("ocr-filter-previews");
                const grayImg = document.getElementById("ocr-preview-gray");
                const threshImg = document.getElementById("ocr-preview-thresh");

                if (previewsBox && grayImg && threshImg) {
                    grayImg.src = data.filter_previews.grayscale;
                    threshImg.src = data.filter_previews.threshold;
                    previewsBox.style.display = "block";
                }
            }

            // Display results
            renderOCRResults(data.extracted_dates, data.best_date);
            showToast("OpenCV image pre-processing complete!", "success");
        } else {
            showToast(data.message || "Could not process image", "danger");
        }
    } catch (err) {
        console.error("OCR error:", err);
        showToast("Failed to upload/process image", "danger");
    } finally {
        if (statusEl) statusEl.textContent = "";
    }
}

// Quick Sample Buttons for Instant Capstone Testing
function testSamplePackaging(type) {
    let mockText = "";
    if (type === "can") {
        mockText = "ARGENTINA CORNED BEEF LOT 4892 EXP: 2027-05-18 BATCH 91A";
    } else if (type === "milk") {
        mockText = "BEAR BRAND STERILIZED BEST BEFORE 15 OCT 2026 14:30";
    } else if (type === "bread") {
        mockText = "GARDENIA CLASSIC CONSUME BY 24/12/2026 SLICED";
    } else if (type === "sardines") {
        mockText = "555 SARDINES IN TOMATO SAUCE EXP 08/2027";
    }

    sendRawTextToOCR(mockText);
}

async function sendRawTextToOCR(rawText) {
    try {
        const res = await fetch("/api/ocr/parse_text", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ raw_text: rawText })
        });
        const data = await res.json();
        if (data.success) {
            renderOCRResults(data.extracted_dates, data.best_date, rawText);
            showToast("Packaging text parsed successfully!", "success");
        }
    } catch (e) {
        showToast("Error parsing packaging text", "danger");
    }
}

function renderOCRResults(extractedDates, bestDate, rawSnippet = "") {
    const resultsBox = document.getElementById("ocr-results-box");
    const displayEl = document.getElementById("ocr-detected-date-display");
    const matchesList = document.getElementById("ocr-matches-list");

    if (!resultsBox || !displayEl) return;
    resultsBox.style.display = "block";

    if (extractedDates && extractedDates.length > 0) {
        displayEl.innerHTML = `<span style="color:var(--brand-primary);font-size:24px;font-weight:800;">${bestDate}</span> 
            <span class="badge badge-success" style="vertical-align:middle;margin-left:8px;">ISO 8601 CONFIRMED</span>`;

        matchesList.innerHTML = extractedDates.map(m => `
            <div style="display:flex;justify-content:space-between;align-items:center;background:var(--bg-surface-elevated);padding:8px 12px;border-radius:6px;margin-bottom:6px;font-size:13px;">
                <div>
                    <strong>Match:</strong> "${m.raw_match}" &nbsp;|&nbsp; 
                    <span style="color:var(--brand-secondary);">Type: ${m.pattern_type}</span>
                </div>
                <button class="btn btn-primary btn-sm" onclick="applyExtractedDate('${m.iso_date}')">
                    Use ${m.iso_date}
                </button>
            </div>
        `).join("");
    } else {
        displayEl.innerHTML = `<span style="color:var(--status-warning);">No expiration date pattern recognized. Try clearer angle or sample button.</span>`;
        matchesList.innerHTML = rawSnippet ? `<div style="font-size:12px;color:var(--text-muted);">Text inspected: "${rawSnippet}"</div>` : "";
    }
}

function applyExtractedDate(isoDate) {
    const target = document.getElementById(OCRScanner.targetInputId);
    if (target) {
        target.value = isoDate;
        showToast(`Applied ${isoDate} to product registration form!`, "success");
    }
    closeOCRModal();
}

window.openOCRModal = openOCRModal;
window.closeOCRModal = closeOCRModal;
window.startCamera = startCamera;
window.stopCamera = stopCamera;
window.captureVideoFrame = captureVideoFrame;
window.testSamplePackaging = testSamplePackaging;
window.applyExtractedDate = applyExtractedDate;
