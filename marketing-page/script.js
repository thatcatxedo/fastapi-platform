const navLinks = document.querySelectorAll('a[href^="#"]');

for (const link of navLinks) {
  link.addEventListener("click", (event) => {
    const href = link.getAttribute("href");
    if (!href || href === "#") {
      return;
    }

    const target = document.querySelector(href);
    if (!target) {
      return;
    }

    event.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

const ctaButtons = document.querySelectorAll(".cta .btn");

for (const button of ctaButtons) {
  button.addEventListener("click", (event) => {
    if (button.getAttribute("href") === "#") {
      event.preventDefault();
      window.alert("Wire this button to your signup, demo, or docs URL.");
    }
  });
}
