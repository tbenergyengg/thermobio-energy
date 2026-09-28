document.addEventListener("DOMContentLoaded", function () {
  const menuBtn = document.querySelector(".menu-btn");
  const navMenu = document.getElementById("navMenu");

  if (menuBtn && navMenu) {
    const mobileStyle = document.createElement("style");
    mobileStyle.textContent = `
      @media (max-width: 820px) {
        #navMenu.mobile-open {
          display:flex !important;
          flex-direction:column !important;
          position:absolute !important;
          top:100% !important;
          left:0 !important;
          right:0 !important;
          z-index:9999 !important;
          background:#fff !important;
          padding:14px 20px 20px !important;
          box-shadow:0 12px 28px rgba(0,0,0,.12) !important;
          border-top:1px solid #e5e7eb !important;
        }
        #navMenu.mobile-open a {
          display:block !important;
          padding:12px 8px !important;
        }
      }
    `;
    document.head.appendChild(mobileStyle);

    menuBtn.addEventListener("click", function(e) {
      e.preventDefault();
      e.stopPropagation();
      navMenu.classList.toggle("mobile-open");
      menuBtn.setAttribute("aria-expanded",
        navMenu.classList.contains("mobile-open") ? "true" : "false");
    });

    navMenu.querySelectorAll("a").forEach(function(link) {
      link.addEventListener("click", function() {
        navMenu.classList.remove("mobile-open");
        menuBtn.setAttribute("aria-expanded", "false");
      });
    });

    document.addEventListener("click", function(e) {
      if (!navMenu.contains(e.target) && !menuBtn.contains(e.target)) {
        navMenu.classList.remove("mobile-open");
        menuBtn.setAttribute("aria-expanded", "false");
      }
    });
  }

  const year = document.getElementById("year");
  if (year) year.textContent = new Date().getFullYear();

  window.submitForm = function(event) {
    event.preventDefault();
    const name = document.getElementById("name")?.value.trim() || "";
    const phone = document.getElementById("phone")?.value.trim() || "";
    const email = document.getElementById("email")?.value.trim() || "";
    const service = document.getElementById("service")?.value || "";
    const message = document.getElementById("message")?.value.trim() || "";
    const text =
      "ThermoBio Website Enquiry%0A" +
      "Name: " + encodeURIComponent(name) + "%0A" +
      "Mobile: " + encodeURIComponent(phone) + "%0A" +
      "Email: " + encodeURIComponent(email) + "%0A" +
      "Service: " + encodeURIComponent(service) + "%0A" +
      "Requirement: " + encodeURIComponent(message);
    window.open("https://wa.me/919006744367?text=" + text, "_blank");
    const formMsg = document.getElementById("formMsg");
    if (formMsg) formMsg.textContent = "Opening WhatsApp to send your enquiry...";
    return false;
  };
});
