function deleteNote(noteId) {
  fetch("/delete-note", {
    method: "POST",
    body: JSON.stringify({ noteId: noteId }),
  }).then((_res) => {
    window.location.href = "/";
  });
}

// Esto se ejecuta cuando la página ha cargado completamente
document.addEventListener('DOMContentLoaded', function() {
  fetchTournaments();  // Esto cargará inicialmente la lista de torneos
});

// Esta función maneja el envío del formulario de creación de torneos
function createTournament(event) {
  event.preventDefault(); // Previene el comportamiento por defecto del formulario
  var formData = new FormData(event.target);  // Aquí tomamos los datos del formulario

  // Enviamos esos datos al servidor con fetch
  fetch('/create-tournament', {
      method: 'POST',
      body: formData
  }).then(response => response.json())
  .then(data => {
      if(data.success) {
          // Si la creación fue exitosa, actualizamos la lista de torneos
          fetchTournaments();
          // Opcional: Cerramos el modal
          $('#createTournamentModal').modal('hide');
          // Opcional: Mostramos un mensaje de éxito
          alert('Torneo creado con éxito.');
      } else {
          // Si hubo un error, mostramos un mensaje
          alert('Error al crear el torneo.');
      }
  }).catch(error => {
      console.error('Error:', error);
  });
}

// Aquí definimos la función que actualiza la lista de torneos en la página
function fetchTournaments() {
  fetch('/get-tournaments')
      .then(response => response.json())
      .then(torneos => {
          const tournamentList = document.getElementById('tournament-list');
          tournamentList.innerHTML = '';  // Limpiamos la lista
          torneos.forEach(torneo => {     // Y la volvemos a llenar con los datos actualizados
              tournamentList.innerHTML += `
                  <div class="tournament-item">
                      <h3>${torneo.nombre}</h3>
                      <p>Fecha: ${torneo.fecha_inicio} - ${torneo.fecha_final}</p>
                      <p>Deporte: ${torneo.deporte}</p>
                      <p>Participantes: ${torneo.equipos_participantes}</p>
                  </div>
              `;
          });
      })
      .catch(error => {
          console.error('Error fetching tournaments:', error);
      });
}

// Necesitas tener un listener para cuando el formulario se envíe
document.getElementById('createTournamentForm').addEventListener('submit', createTournament);

