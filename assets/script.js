// Compartir y copiar enlace — sin dependencias.
(function(){
  document.querySelectorAll('[data-copy]').forEach(function(btn){
    btn.addEventListener('click', function(){
      var url = btn.getAttribute('data-copy');
      var original = btn.querySelector('.copy-label');
      function done(ok){
        if(!original) return;
        original.textContent = ok ? 'Enlace copiado' : 'No se pudo copiar';
        setTimeout(function(){ original.textContent = 'Copiar enlace'; }, 1800);
      }
      try{
        navigator.clipboard.writeText(url).then(function(){done(true)}, function(){done(false)});
      }catch(e){ done(false); }
    });
  });
})();
