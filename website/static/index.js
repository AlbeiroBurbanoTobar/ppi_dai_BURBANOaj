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
          const select = document.getElementById('tournamentSelect');
          data.forEach(torneo => {
            const option = document.createElement('option');
            option.value = torneo.id;
            option.textContent = torneo.nombre;
            select.appendChild(option);
        });
    })
    .catch(error => console.error('Error al cargar torneos:', error));
}

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


// Necesitas tener un listener para cuando el formulario se envíe
document.getElementById('createTournamentForm').addEventListener('submit', createTournament);

document.addEventListener('DOMContentLoaded', function() {
  fetchTeams();
});

// Se agrega un listener al botón que abre el modal de "Ver Equipos"
$('#viewTeamsModal').on('show.bs.modal', function () {
  fetchTeams();
});

function fetchTeams() {
  fetch('/get-teams')
      .then(response => response.json())
      .then(teams => {
          const teamList = document.getElementById('list-of-teams');
          teamList.innerHTML = '';
          teams.forEach(team => {
              const li = document.createElement('li');
              li.classList.add('list-group-item');
              li.textContent = `${team.TeamName} - Capitán: ${team.CaptainName} - Contacto: ${team.CaptainContact}`;
              teamList.appendChild(li);
          });
      })
      .catch(error => {
          console.error('Error al cargar los equipos:', error);
          alert('Error al cargar los equipos');
      });
}

// Asumiendo que jQuery está habilitado
$(document).ready(function() {
  $('#playersModal').on('show.bs.modal', function (event) {
      var button = $(event.relatedTarget);  // Botón que activó el modal
      var teamId = button.data('id');  // Extraer información del atributo data-*

      // Limpia la tabla anterior
      $('#playersData').empty();

      // Carga de datos de jugadores mediante AJAX
      $.getJSON('/get-players/' + teamId, function(data) {
          $.each(data, function(index, player) {
              var row = `<tr>
                          <td>${player.FirstName}</td>
                          <td>${player.LastName}</td>
                          <td>${player.Age}</td>
                         </tr>`;
              $('#playersData').append(row);
          });
      });
  });
});


$(document).ready(function() {
  $('#playersModal').on('show.bs.modal', function (event) {
      var button = $(event.relatedTarget);  // Botón que activó el modal
      var teamId = button.data('id');  // Extraer información del atributo data-*

      // Limpia la tabla anterior
      $('#playersData').empty();

      // Carga de datos de jugadores mediante AJAX
      $.getJSON('/get-players/' + teamId, function(data) {
          if(data.length === 0) {
              $('#playersData').append('<tr><td colspan="3">No hay jugadores registrados en este equipo.</td></tr>');
          } else {
              $.each(data, function(index, player) {
                  var row = `<tr>
                              <td>${player.FirstName}</td>
                              <td>${player.LastName}</td>
                              <td>${player.Age}</td>
                             </tr>`;
                  $('#playersData').append(row);
              });
          }
      }).fail(function() {
          console.log("Error al cargar los datos.");
      });
  });
});


