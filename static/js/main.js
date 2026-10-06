document.querySelectorAll('.alert').forEach((alert) => {
    setTimeout(() => {
        if (window.bootstrap) bootstrap.Alert.getOrCreateInstance(alert).close();
    }, 6000);
});

const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
        if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            revealObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.12 });
document.querySelectorAll('.reveal').forEach((el) => revealObserver.observe(el));
