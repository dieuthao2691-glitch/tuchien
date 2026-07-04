// MOBILE NAVIGATION MENU
const mobileNavToggle = document.getElementById('mobileNavToggle');
const mobileMenu = document.getElementById('mobileMenu');

if (mobileNavToggle && mobileMenu) {
    mobileNavToggle.addEventListener('click', () => {
        mobileMenu.classList.toggle('active');
        mobileNavToggle.classList.toggle('active');
        
        const spans = mobileNavToggle.querySelectorAll('span');
        if (mobileMenu.classList.contains('active')) {
            spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
            spans[1].style.opacity = '0';
            spans[2].style.transform = 'rotate(-45deg) translate(6px, -6px)';
        } else {
            spans[0].style.transform = 'none';
            spans[1].style.opacity = '1';
            spans[2].style.transform = 'none';
        }
    });

    const mobileLinks = mobileMenu.querySelectorAll('.mobile-link');
    mobileLinks.forEach(link => {
        link.addEventListener('click', () => {
            mobileMenu.classList.remove('active');
            const spans = mobileNavToggle.querySelectorAll('span');
            spans[0].style.transform = 'none';
            spans[1].style.opacity = '1';
            spans[2].style.transform = 'none';
        });
    });
}

// BACK TO TOP BUTTON LOGIC
const backToTopBtn = document.getElementById('backToTop');
if (backToTopBtn) {
    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) {
            backToTopBtn.classList.add('active');
        } else {
            backToTopBtn.classList.remove('active');
        }
    });

    backToTopBtn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

// GENERAL MODAL LOGIC
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function openTourModal() {
    openModal('tour-modal');
}

// Close modals on outside click
window.addEventListener('click', (e) => {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (e.target === modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
});

// DYNAMIC PAYMENT MODAL
let currentCaptchaCode = '';

function generateCaptcha() {
    const chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'; // Exclude confusing chars like 0, 1, O, I
    let result = '';
    for (let i = 0; i < 4; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    currentCaptchaCode = result;
    const captchaBox = document.getElementById('captcha-code');
    if (captchaBox) {
        captchaBox.textContent = result;
    }
}

function copyText(elementId, btn) {
    const textSpan = document.getElementById(elementId);
    if (!textSpan) return;
    const text = textSpan.textContent.trim();
    
    navigator.clipboard.writeText(text).then(() => {
        const originalText = btn.textContent;
        btn.textContent = '✓';
        btn.style.color = 'var(--color-secondary)';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.color = '';
        }, 1500);
    }).catch(err => {
        // Fallback for copy on older browsers / HTTP environments
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            const originalText = btn.textContent;
            btn.textContent = '✓';
            btn.style.color = 'var(--color-secondary)';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.color = '';
            }, 1500);
        } catch (copyErr) {
            alert('Không thể tự động sao chép. Chị vui lòng bôi đen và sao chép thủ công nhé!');
        }
        document.body.removeChild(textarea);
    });
}

function openPaymentModal(serviceName, price) {
    const payServiceName = document.getElementById('pay-service-name');
    const payServicePrice = document.getElementById('pay-service-price');
    const payMessage = document.getElementById('pay-message');
    const qrImage = document.getElementById('qr-code-image');
    const btnDownloadQr = document.getElementById('btn-download-qr');
    
    // Build a banking-safe slug from serviceName (ASCII only, max 20 chars)
    function makeSlug(name) {
        return name
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '') // remove diacritics
            .replace(/[^a-zA-Z0-9]/g, '')    // keep alphanumeric only
            .toUpperCase()
            .substring(0, 20);
    }
    
    const serviceSlug = makeSlug(serviceName);
    
    if (payServiceName && payServicePrice && payMessage) {
        payServiceName.textContent = serviceName;
        payServicePrice.textContent = price.toLocaleString('vi-VN') + 'đ';
        
        // Initial message: SLUG_ (phone not yet entered)
        const cleanMessage = serviceSlug + '_';
        payMessage.textContent = cleanMessage;
        
        // Set dynamic VietQR code image source using MB Bank (970422), STK 123456789
        const qrUrl = `https://img.vietqr.io/image/MB-123456789-compact2.jpg?amount=${price}&addInfo=${encodeURIComponent(cleanMessage)}&accountName=TUC%20HIEN`;
        if (qrImage) qrImage.src = qrUrl;
        if (btnDownloadQr) btnDownloadQr.href = qrUrl;
        
        const payPhoneInput = document.getElementById('pay-phone');
        if (payPhoneInput) {
            // Remove previous event listener by replacing the node to avoid duplicate events
            const newPhoneInput = payPhoneInput.cloneNode(true);
            payPhoneInput.parentNode.replaceChild(newPhoneInput, payPhoneInput);
            
            newPhoneInput.addEventListener('input', (e) => {
                const sdt = e.target.value.replace(/[^0-9]/g, '');
                const updatedMessage = serviceSlug + '_' + sdt;
                payMessage.textContent = updatedMessage;
                
                // Update VietQR dynamic image and download link as phone number changes
                const updatedQrUrl = `https://img.vietqr.io/image/MB-123456789-compact2.jpg?amount=${price}&addInfo=${encodeURIComponent(updatedMessage)}&accountName=TUC%20HIEN`;
                if (qrImage) qrImage.src = updatedQrUrl;
                if (btnDownloadQr) btnDownloadQr.href = updatedQrUrl;
            });
        }
        
        generateCaptcha();
        openModal('payment-modal');
    }
}

// FORM SUBMISSIONS
function handleConsultSubmit(event) {
    event.preventDefault();
    const name = document.getElementById('consult-name').value;
    const phone = document.getElementById('consult-phone').value;
    const service = document.getElementById('consult-service').value;
    
    alert(`Cảm ơn chị ${name}!\nYêu cầu tư vấn của chị đã được Túc Hiên tiếp nhận.\nChúng tôi sẽ gọi lại cho chị qua số điện thoại ${phone} trong vòng 2 giờ làm việc.`);
    document.getElementById('consultForm').reset();
    closeModal('consult-modal');
}

function handlePaymentSubmit(event) {
    event.preventDefault();
    const name = document.getElementById('pay-name').value;
    const phone = document.getElementById('pay-phone').value;
    const email = document.getElementById('pay-email').value;
    const service = document.getElementById('pay-service-name').textContent;
    
    // Captcha validation
    const typedCaptcha = document.getElementById('pay-captcha').value.trim().toUpperCase();
    if (typedCaptcha !== currentCaptchaCode) {
        alert("Mã xác thực (Captcha) không chính xác. Vui lòng nhập lại!");
        document.getElementById('pay-captcha').value = '';
        generateCaptcha();
        return;
    }
    
    alert(`Cảm ơn chị ${name}!\nTúc Hiên đã tiếp nhận thông tin xác nhận chuyển khoản cho dịch vụ: "${service}".\nChúng tôi sẽ đối soát giao dịch và liên hệ lại với chị qua số điện thoại ${phone} hoặc email ${email} để gửi vé xác nhận ngay lập tức.`);
    document.getElementById('paymentForm').reset();
    closeModal('payment-modal');
}

function handleTourSubmit(event) {
    event.preventDefault();
    const name = document.getElementById('tour-name').value;
    const phone = document.getElementById('tour-phone').value;
    const date = document.getElementById('tour-date').value;
    
    closeModal('tour-modal');
    
    // Open payment modal for Tour
    openPaymentModal(`Tour Vườn Thảo Dược Ngok Linh (${date})`, 2000000);
    
    // Pre-fill name and phone in payment form
    const payName = document.getElementById('pay-name');
    const payPhone = document.getElementById('pay-phone');
    if (payName) payName.value = name;
    if (payPhone) {
        payPhone.value = phone;
        // Trigger input event to update QR message
        payPhone.dispatchEvent(new Event('input'));
    }
    
    document.getElementById('tourForm').reset();
}

// ─────────────────────────────────────────────────
//  INTERACTIVE QUIZ LOGIC (Multiple-choice, manual advance)
// ─────────────────────────────────────────────────

// Stores ARRAYS of selected values per step
let quizAnswers = {
    step1: [],
    step2: [],
    step3: []
};

// Toggle .selected on option buttons (multiple choice, no auto-advance)
document.querySelectorAll('.option-btn').forEach(button => {
    button.addEventListener('click', () => {
        button.classList.toggle('selected');
    });
});

// Navigate to a step (show it, hide all others)
function goToStep(stepId) {
    document.querySelectorAll('.quiz-step').forEach(step => {
        step.classList.remove('active');
    });
    const target = document.getElementById(stepId);
    if (target) target.classList.add('active');
}

// Collect selected answers from a step and advance to next step
function advanceQuiz(currentStepId, nextStepId) {
    const currentStep = document.getElementById(currentStepId);
    if (!currentStep) return;

    // Collect all selected option values in the current step
    const selectedBtns = currentStep.querySelectorAll('.option-btn.selected');
    const selectedValues = Array.from(selectedBtns).map(btn => btn.getAttribute('data-value'));
    quizAnswers[currentStepId] = selectedValues;

    if (nextStepId === 'stepResult') {
        calculateQuizResult();
    } else {
        goToStep(nextStepId);
    }
}

// Go back to previous step and clear current step's selections
function goBackToStep(prevStepId) {
    // Find and deselect all currently visible options in the active step
    const activeStep = document.querySelector('.quiz-step.active');
    if (activeStep) {
        activeStep.querySelectorAll('.option-btn.selected').forEach(btn => {
            btn.classList.remove('selected');
        });
        // Clear stored answers for this step
        quizAnswers[activeStep.id] = [];
    }
    goToStep(prevStepId);
}

// Reset entire quiz
function resetQuiz() {
    quizAnswers = { step1: [], step2: [], step3: [] };
    // Clear all .selected states
    document.querySelectorAll('.option-btn.selected').forEach(btn => {
        btn.classList.remove('selected');
    });
    goToStep('step1');
}

// Calculate result based on collected multi-select answers
function calculateQuizResult() {
    const s1 = quizAnswers.step1; // array
    const s2 = quizAnswers.step2; // array
    const s3 = quizAnswers.step3; // array

    let recName = '';
    let recPrice = 0;
    let titleText = '';
    let descText = '';

    const has = (arr, val) => arr.includes(val);

    // Priority logic: most comprehensive need → intensive package
    const wantsAll = s1.length >= 2 || (s1.length >= 1 && s2.length >= 2 && s3.length >= 2);
    const wantsNature = has(s1, 'disconnection') || has(s2, 'trip') || has(s3, 'nature');
    const wantsMental = has(s1, 'mental') || has(s2, 'weekend') || has(s3, 'yoga');
    const wantsPhysical = has(s1, 'physical') || has(s3, 'herbs');

    if (wantsAll) {
        recName = 'Gói Trị Liệu Chuyên Sâu Túc Hiên';
        recPrice = 4500000;
        titleText = 'Lộ trình Chuyên sâu Toàn diện';
        descText = 'Cơ thể và tâm trí của bạn đang cần một giải pháp kết hợp bài bản giữa Yoga cổ điển Ấn Độ, Y học cổ truyền và trị liệu tâm lý sâu sắc. Gói chuyên sâu của Túc Hiên được thiết kế riêng cho bạn.';
    } else if (wantsNature) {
        recName = 'Trải Nghiệm Thiên Nhiên Phục Hồi';
        recPrice = 1000000;
        titleText = 'Hành trình phục hồi năng lượng xanh';
        descText = 'Bạn đang thiếu kết nối với thiên nhiên và cần ngắt màn hình. Một chuyến trekking nhẹ nhàng tại suối rừng cùng các kỹ thuật thở ngoài trời sẽ giúp cơ thể bạn sạc lại năng lượng tự nhiên.';
    } else if (wantsMental) {
        recName = 'Workshop Chuyên Đề Thực Tế';
        recPrice = 350000;
        titleText = 'Cải thiện Thể tạng & Khắc phục Đau mỏi';
        descText = 'Áp lực tâm lý và mệt mỏi tinh thần là vấn đề cốt lõi của bạn. Tham gia các buổi workshop cuối tuần giúp bạn thực hành Yoga cổ điển, nhận biết thể tạng và tự chăm sóc cơ xương khớp tại nhà.';
    } else {
        recName = 'Thảo Dược & Y Học Cổ Truyền';
        recPrice = 500000;
        titleText = 'Thảo dược & Trị liệu Y học cổ truyền';
        descText = 'Cơ thể bạn có dấu hiệu mất cân bằng thể chất. Trị liệu bằng xoa bóp bấm huyệt kết hợp các loại thảo dược ăn/uống/xông/tắm sẽ giúp khai thông và phục hồi sức sống tự nhiên.';
    }

    // Render result
    document.getElementById('resultTitle').textContent = titleText;
    document.getElementById('resultDesc').textContent = descText;
    document.getElementById('recommendedServiceName').textContent = recName;
    document.getElementById('recommendedServicePrice').textContent = recPrice.toLocaleString('vi-VN') + 'đ';

    // Hook pay button dynamically
    const btnQuizPay = document.getElementById('btnQuizPay');
    if (btnQuizPay) {
        const newBtn = btnQuizPay.cloneNode(true);
        btnQuizPay.parentNode.replaceChild(newBtn, btnQuizPay);
        newBtn.addEventListener('click', () => {
            openPaymentModal(recName, recPrice);
        });
    }

    goToStep('stepResult');
}

// SHARE WEBSITE FUNCTION
function shareWebsite() {
    const dummyUrl = window.location.href;
    navigator.clipboard.writeText(dummyUrl).then(() => {
        const btnShare = document.getElementById('btnShare');
        const spanText = btnShare && btnShare.querySelector('span');
        if (spanText) {
            const originalText = spanText.textContent;
            spanText.textContent = 'Đã sao chép liên kết!';
            btnShare.style.borderColor = 'var(--color-secondary)';
            btnShare.style.color = 'var(--color-secondary)';
            setTimeout(() => {
                spanText.textContent = originalText;
                btnShare.style.borderColor = '';
                btnShare.style.color = '';
            }, 3000);
        }
    }).catch(err => {
        alert('Chị có thể sao chép đường link trên trình duyệt để chia sẻ nhé!');
    });
}

// ─────────────────────────────────────────────────
//  SERVICE PACKAGE DETAILS DIALOG LOGIC
// ─────────────────────────────────────────────────
const serviceDetails = {
    'herbs': {
        title: 'Thảo Dược & Y Học Cổ Truyền',
        price: 500000,
        description: `
            <p>Liệu pháp phục hồi sức khỏe tự nhiên kết hợp thảo dược lành tính (ăn, uống, xông, tắm, bôi) với các liệu pháp trị liệu vật lý chuẩn y khoa như xoa bóp, bấm huyệt và châm cứu.</p>
            <h4 style="margin-top: 1.5rem; margin-bottom: 0.5rem; font-family: var(--font-heading); color: var(--color-text-dark);">Dịch vụ bao gồm:</h4>
            <ul style="padding-left: 1.25rem; margin-bottom: 1.5rem; font-size: 0.9rem; color: var(--color-text-muted); line-height: 1.6;">
                <li style="margin-bottom: 0.5rem;"><strong>Trị liệu cổ vai gáy & thắt lưng:</strong> Giải tỏa các điểm căng cơ cơ học bằng kỹ thuật xoa bóp bấm huyệt chuyên sâu.</li>
                <li style="margin-bottom: 0.5rem;"><strong>Xông tắm thảo dược cổ truyền:</strong> Đào thải độc tố cơ thể qua hệ bài tiết dưới da, kích thích tuần hoàn máu toàn thân.</li>
                <li style="margin-bottom: 0.5rem;"><strong>Châm cứu trị liệu (tùy chọn):</strong> Tác động sâu vào hệ kinh lạc giúp đả thông khí huyết, điều hòa giấc ngủ.</li>
                <li style="margin-bottom: 0.5rem;"><strong>Thực dưỡng & Trà thảo mộc:</strong> Dùng trà thanh lọc cơ thể và các món nhẹ từ dược liệu nuôi trồng tự nhiên.</li>
            </ul>
            <p style="font-size: 0.85rem; font-style: italic; color: var(--color-text-muted);">* Liệu trình sẽ được thiết kế cá nhân hóa dựa trên kết quả kiểm tra thể trạng trực tiếp tại Túc Hiên.</p>
        `
    },
    'workshop': {
        title: 'Workshop Chuyên Đề Thực Tế',
        price: 350000,
        description: `
            <p>Các buổi thực hành chuyên đề thực tế giúp bạn có đủ kiến thức và kỹ năng để tự chăm sóc sức khỏe chủ động tại nhà.</p>
            <h4 style="margin-top: 1.5rem; margin-bottom: 0.5rem; font-family: var(--font-heading); color: var(--color-text-dark);">Chi tiết các chuyên đề workshop:</h4>
            <ul style="padding-left: 1.25rem; margin-bottom: 1.5rem; font-size: 0.9rem; color: var(--color-text-muted); line-height: 1.6;">
                <li style="margin-bottom: 0.5rem;"><strong>WS1: Khắc phục đau cổ vai gáy văn phòng:</strong> Hướng dẫn tư thế ngồi chuẩn, bài tập kéo giãn Yoga phục hồi cơ xương khớp và bài tự xoa bóp bấm huyệt thông kinh lạc vùng cổ gáy.</li>
                <li style="margin-bottom: 0.5rem;"><strong>WS2: Định hình thể tạng & dinh dưỡng cân bằng:</strong> Xác định thể tạng (Prakriti) theo Ayurveda cổ điển Ấn Độ, từ đó thiết kế thực đơn ăn uống và thói quen sinh hoạt thích ứng để phòng bệnh từ gốc.</li>
            </ul>
            <p style="font-size: 0.85rem; font-style: italic; color: var(--color-text-muted);">* Workshop được tổ chức vào các ngày cuối tuần (Thứ Bảy/Chủ Nhật), số lượng học viên giới hạn để đảm bảo chất lượng hướng dẫn.</p>
        `
    },
    'nature': {
        title: 'Vận Động & Trải Nghiệm Thiên Nhiên Phục Hồi',
        price: 1000000,
        description: `
            <p>Hành trình dã ngoại, ngắt kết nối màn hình điện tử hoàn toàn để thiết lập lại đồng hồ sinh học tự nhiên giữa thiên nhiên hoang sơ.</p>
            <h4 style="margin-top: 1.5rem; margin-bottom: 0.5rem; font-family: var(--font-heading); color: var(--color-text-dark);">Nội dung trải nghiệm:</h4>
            <ul style="padding-left: 1.25rem; margin-bottom: 1.5rem; font-size: 0.9rem; color: var(--color-text-muted); line-height: 1.6;">
                <li style="margin-bottom: 0.5rem;"><strong>Trekking & Đi bộ thiền định:</strong> Hành trình di chuyển cự ly ngắn (3-5km) xuyên qua những cánh rừng mộc mạc Ngọc Linh để kết nối lại các giác quan thể chất.</li>
                <li style="margin-bottom: 0.5rem;"><strong>Cắm trại phục hồi bên suối:</strong> Nghỉ ngơi trong lều trại cao cấp, nghe tiếng nước chảy, ăn đồ ăn thực dưỡng chế biến trực tiếp tại chỗ.</li>
                <li style="margin-bottom: 0.5rem;"><strong>Kỹ thuật Pranayama (Tập thở ngoài trời):</strong> Luyện thở lấy sinh khí sáng sớm tại bờ suối kết hợp bài tập chánh niệm nhẹ nhàng.</li>
            </ul>
            <p style="font-size: 0.85rem; font-style: italic; color: var(--color-text-muted);">* Chi phí đã bao gồm lều trại, ăn uống thực dưỡng 3 bữa và hướng dẫn viên đồng hành suốt tuyến.</p>
        `
    },
    'intensive': {
        title: 'Gói Trị Liệu Chuyên Sâu Túc Hiên',
        price: 4500000,
        description: `
            <p>Giải pháp phục hồi sức khỏe đặc biệt nhất của Túc Hiên, can thiệp sâu sắc và toàn diện nhằm thiết lập lại trạng thái cân bằng vững vàng trên cả ba khía cạnh Thân - Tâm - Trí.</p>
            <h4 style="margin-top: 1.5rem; margin-bottom: 0.5rem; font-family: var(--font-heading); color: var(--color-text-dark);">Quy trình đồng hành 4 tuần:</h4>
            <ul style="padding-left: 1.25rem; margin-bottom: 1.5rem; font-size: 0.9rem; color: var(--color-text-muted); line-height: 1.6;">
                <li style="margin-bottom: 0.5rem;"><strong>Tuần 1: Chẩn đoán & Thải độc:</strong> Đánh giá chi tiết thể tạng bởi bác sĩ, bắt đầu liệu trình uống/tắm xông thảo dược để thanh lọc tích tụ thể chất.</li>
                <li style="margin-bottom: 0.5rem;"><strong>Tuần 2: Phục hồi năng lượng:</strong> Các buổi xoa bóp trị liệu sâu kết hợp học cách kiểm soát hơi thở để làm dịu hệ thần kinh trung ương.</li>
                <li style="margin-bottom: 0.5rem;"><strong>Tuần 3: Trị liệu cảm xúc (Tâm - Trí):</strong> Tham vấn cá nhân tháo gỡ căng thẳng, định hướng tư duy lành mạnh dưới góc nhìn của triết lý sống Yoga Ấn Độ cổ đại.</li>
                <li style="margin-bottom: 0.5rem;"><strong>Tuần 4: Kiến tạo lối sống tự lực:</strong> Xây dựng cuốn cẩm nang dinh dưỡng và bài tập hàng ngày giúp bạn duy trì sức khỏe bền bỉ khi trở lại nhịp sống thường nhật.</li>
            </ul>
            <p style="font-size: 0.85rem; font-style: italic; color: var(--color-text-muted);">* Gói dịch vụ cao cấp nhất, số lượng nhận đăng ký giới hạn chỉ 5 khách hàng mỗi tháng.</p>
        `
    }
};

function openDetailModal(key) {
    const details = serviceDetails[key];
    if (!details) return;

    const detailTitle = document.getElementById('detail-title');
    const detailBody = document.getElementById('detail-body');
    const btnPay = document.getElementById('detail-btn-pay');
    
    if (detailTitle && detailBody && btnPay) {
        detailTitle.textContent = details.title;
        detailBody.innerHTML = details.description;
        
        // Recreate pay button to clear old event listeners
        const newBtn = btnPay.cloneNode(true);
        btnPay.parentNode.replaceChild(newBtn, btnPay);
        newBtn.addEventListener('click', () => {
            closeModal('detail-modal');
            openPaymentModal(details.title, details.price);
        });
        
        openModal('detail-modal');
    }
}

