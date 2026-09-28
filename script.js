async function submitForm(event) {
  event.preventDefault();

  const form = document.getElementById('contactForm');
  const name = document.getElementById('name').value.trim();
  const phone = document.getElementById('phone').value.trim();
  const email = document.getElementById('email').value.trim();
  const service = document.getElementById('service').value;
  const message = document.getElementById('message').value.trim();
  const formMsg = document.getElementById('formMsg');
  const submitButton = form.querySelector('button[type="submit"]');

  const subject = `New Website Enquiry - ${service}`;
  const body = `New enquiry from ThermoBio website\n\nName: ${name}\nMobile: ${phone}\nEmail: ${email || 'Not provided'}\nService: ${service}\nRequirement: ${message || 'Not provided'}`;

  // WhatsApp destination: +91 90067 44367
  const whatsappNumber = '919006744367';
  const whatsappUrl = `https://wa.me/${whatsappNumber}?text=${encodeURIComponent(body)}`;

  // Send enquiry automatically to ThermoBio Gmail through FormSubmit.
  // On the first successful submission, FormSubmit may send an activation email
  // to tbenergy.engg@gmail.com. Activate it once; later enquiries are automatic.
  const emailEndpoint = 'https://formsubmit.co/ajax/tbenergy.engg@gmail.com';

  submitButton.disabled = true;
  submitButton.textContent = 'Sending...';
  formMsg.textContent = 'Sending your enquiry...';
  formMsg.style.display = 'block';

  try {
    const response = await fetch(emailEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({
        name,
        phone,
        email: email || 'Not provided',
        service,
        message: message || 'Not provided',
        _subject: subject,
        _template: 'table',
        _captcha: 'false'
      })
    });

    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.message || 'Email service error');

    // Open WhatsApp after the enquiry has been accepted for email delivery.
    window.open(whatsappUrl, '_blank', 'noopener');
    formMsg.textContent = 'Enquiry sent to ThermoBio email and WhatsApp (+91 90067 44367).';
    formMsg.style.display = 'block';
    form.reset();
  } catch (error) {
    // Even if email delivery is unavailable, still provide the WhatsApp enquiry path.
    window.open(whatsappUrl, '_blank', 'noopener');
    formMsg.textContent = 'WhatsApp enquiry opened. Email delivery needs activation/setup.';
    formMsg.style.display = 'block';
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = 'Submit Enquiry';
  }

  return false;
}

document.addEventListener('DOMContentLoaded', () => {
  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
});
