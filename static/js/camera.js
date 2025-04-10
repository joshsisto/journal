/**
 * Camera functionality for Journal App
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log("Initializing camera functionality");
    
    // Get all the necessary elements
    const cameraBtn = document.getElementById('camera-btn');
    const cameraModal = document.getElementById('cameraModal');
    const captureBtn = document.getElementById('capture-btn');
    const videoElement = document.getElementById('camera-preview');
    const canvasElement = document.getElementById('camera-canvas');
    const errorElement = document.getElementById('camera-error');
    const photoInput = document.getElementById('photos');
    const photoPreview = document.getElementById('photo-preview');
    
    // Return early if we're not on a page with camera functionality
    if (!cameraBtn || !cameraModal || !videoElement || !captureBtn) {
        console.log("Camera elements not found on this page");
        return;
    }
    
    let stream = null;
    let bootstrapModal = null;
    
    // Initialize bootstrap modal
    function initModal() {
        if (typeof bootstrap !== 'undefined') {
            try {
                bootstrapModal = new bootstrap.Modal(cameraModal);
                console.log("Bootstrap modal initialized");
            } catch (err) {
                console.error("Error initializing bootstrap modal:", err);
            }
        } else {
            console.warn("Bootstrap not available yet, retrying in 100ms");
            setTimeout(initModal, 100);
        }
    }
    
    // First attempt to initialize the modal
    initModal();
    
    // Function to add captured image to form
    function addCapturedImageToForm(dataUrl) {
        try {
            console.log("Adding captured image to form");
            
            // Convert data URL to Blob
            const byteString = atob(dataUrl.split(',')[1]);
            const mimeType = dataUrl.split(',')[0].split(':')[1].split(';')[0];
            const ab = new ArrayBuffer(byteString.length);
            const ia = new Uint8Array(ab);
            
            for (let i = 0; i < byteString.length; i++) {
                ia[i] = byteString.charCodeAt(i);
            }
            
            const blob = new Blob([ab], { type: mimeType });
            
            // Create File object from Blob
            const filename = `camera_${new Date().toISOString()}.jpg`;
            const file = new File([blob], filename, { type: 'image/jpeg' });
            
            // Add to preview
            const imgContainer = document.createElement('div');
            imgContainer.className = 'position-relative';
            
            const img = document.createElement('img');
            img.src = dataUrl;
            img.className = 'img-thumbnail';
            img.style.maxHeight = '150px';
            img.style.maxWidth = '200px';
            imgContainer.appendChild(img);
            photoPreview.appendChild(imgContainer);
            
            // Try to add to file input using DataTransfer API
            try {
                if (typeof DataTransfer !== 'undefined') {
                    const dataTransfer = new DataTransfer();
                    
                    // Add existing files
                    if (photoInput.files) {
                        for (let i = 0; i < photoInput.files.length; i++) {
                            dataTransfer.items.add(photoInput.files[i]);
                        }
                    }
                    
                    // Add new file
                    dataTransfer.items.add(file);
                    photoInput.files = dataTransfer.files;
                    console.log("Successfully added file using DataTransfer API");
                } else {
                    throw new Error("DataTransfer API not available");
                }
            } catch (err) {
                console.warn("DataTransfer API error:", err);
                
                // Create a hidden field to indicate we have captured photos
                let hiddenField = document.getElementById('has-captured-photos');
                if (!hiddenField) {
                    hiddenField = document.createElement('input');
                    hiddenField.type = 'hidden';
                    hiddenField.id = 'has-captured-photos';
                    hiddenField.name = 'has_captured_photos';
                    hiddenField.value = 'true';
                    photoInput.parentNode.appendChild(hiddenField);
                }
                
                // Store the file in a global array so we can handle it later
                if (!window.capturedPhotos) {
                    window.capturedPhotos = [];
                }
                window.capturedPhotos.push(file);
                console.log("Added photo to window.capturedPhotos array");
            }
        } catch (err) {
            console.error("Error adding image to form:", err);
            alert("There was an error processing the captured image.");
        }
    }
    
    // Camera button click handler
    cameraBtn.addEventListener('click', function() {
        console.log("Camera button clicked");
        
        if (errorElement) {
            errorElement.style.display = 'none';
        }
        
        // Check if we're in a secure context (HTTPS or localhost)
        const isSecureContext = window.isSecureContext || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
        if (!isSecureContext) {
            console.error("Camera access requires a secure context (HTTPS)");
            if (errorElement) {
                errorElement.textContent = "Camera access requires HTTPS. Your connection is not secure.";
                errorElement.style.display = "block";
                
                // Still show modal to display error
                if (bootstrapModal) {
                    bootstrapModal.show();
                }
            } else {
                alert("Camera access requires HTTPS. Your connection is not secure.");
            }
            return;
        }
        
        // Check if the browser supports camera access
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.error("getUserMedia not supported in this browser");
            if (errorElement) {
                errorElement.textContent = "Your browser doesn't support camera access";
                errorElement.style.display = "block";
                
                // Still show modal to display error
                if (bootstrapModal) {
                    bootstrapModal.show();
                }
            }
            return;
        }
        
        // Ensure Bootstrap is loaded
        if (!bootstrapModal) {
            console.warn("Bootstrap modal not initialized yet, retrying");
            initModal();
            if (!bootstrapModal) {
                alert("Camera interface is not ready yet. Please try again in a moment.");
                return;
            }
        }
        
        // Get camera access
        navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'environment', // Prefer back camera if available
                width: { ideal: 1280 },
                height: { ideal: 720 }
            },
            audio: false
        })
        .then(function(mediaStream) {
            console.log("Camera access granted");
            
            // Stop any existing stream
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
            
            // Save the stream and set it to the video element
            stream = mediaStream;
            videoElement.srcObject = stream;
            
            // Play the video
            videoElement.play()
                .then(() => console.log("Video playback started"))
                .catch(err => console.error("Error playing video:", err));
            
            // Show the modal
            bootstrapModal.show();
        })
        .catch(function(err) {
            console.error("Error accessing camera:", err);
            
            let errorMessage = "Camera error: ";
            if (err.name === 'NotAllowedError') {
                errorMessage += "Permission denied. Please allow camera access.";
            } else if (err.name === 'NotFoundError') {
                errorMessage += "No camera found on your device.";
            } else if (err.name === 'NotReadableError') {
                errorMessage += "Camera is in use by another application.";
            } else {
                errorMessage += err.message || "Unknown error";
            }
            
            if (errorElement) {
                errorElement.textContent = errorMessage;
                errorElement.style.display = "block";
            }
            
            // Still show the modal to display the error
            if (bootstrapModal) {
                bootstrapModal.show();
            }
        });
    });
    
    // Capture button click handler
    captureBtn.addEventListener('click', function() {
        console.log("Capture button clicked");
        
        if (!stream) {
            console.error("No active camera stream");
            return;
        }
        
        try {
            // Get video dimensions
            const width = videoElement.videoWidth;
            const height = videoElement.videoHeight;
            
            if (!width || !height) {
                throw new Error("Video dimensions not available");
            }
            
            console.log(`Video dimensions: ${width}x${height}`);
            
            // Set canvas dimensions
            canvasElement.width = width;
            canvasElement.height = height;
            
            // Draw video frame to canvas
            const context = canvasElement.getContext('2d');
            context.drawImage(videoElement, 0, 0, width, height);
            
            // Get image data URL
            const imageDataUrl = canvasElement.toDataURL('image/jpeg', 0.9);
            
            // Add to form
            addCapturedImageToForm(imageDataUrl);
            
            // Close modal and stop camera
            if (bootstrapModal) {
                bootstrapModal.hide();
            }
            
            // Stop the stream
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
                stream = null;
            }
        } catch (err) {
            console.error("Error capturing photo:", err);
            if (errorElement) {
                errorElement.textContent = `Error capturing photo: ${err.message}`;
                errorElement.style.display = 'block';
            }
        }
    });
    
    // Clean up when modal is closed
    cameraModal.addEventListener('hidden.bs.modal', function() {
        console.log("Modal closed, stopping camera");
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
    });
    
    // Handle form submission with captured photos
    const forms = document.querySelectorAll('form[enctype="multipart/form-data"]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (window.capturedPhotos && window.capturedPhotos.length > 0) {
                console.log(`Handling ${window.capturedPhotos.length} captured photos on form submission`);
                
                // If we have captured photos but couldn't add them to the input via DataTransfer,
                // we need to handle the submission manually
                
                // We'll only do this if a specific flag is present
                const hasCaptures = document.getElementById('has-captured-photos');
                if (hasCaptures) {
                    e.preventDefault();
                    
                    const formData = new FormData(this);
                    
                    // Add captured photos
                    window.capturedPhotos.forEach((file, index) => {
                        formData.append('photos', file);
                        console.log(`Added photo ${index + 1}: ${file.name}`);
                    });
                    
                    // Submit via fetch
                    fetch(this.action, {
                        method: this.method,
                        body: formData
                    })
                    .then(response => {
                        if (response.redirected) {
                            window.location.href = response.url;
                        } else {
                            return response.text();
                        }
                    })
                    .then(html => {
                        if (html) {
                            document.documentElement.innerHTML = html;
                        }
                    })
                    .catch(error => {
                        console.error("Error submitting form:", error);
                        alert("There was an error submitting the form. Please try again.");
                    });
                }
            }
        });
    });
});