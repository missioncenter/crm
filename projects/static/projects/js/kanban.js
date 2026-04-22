function getCookie(name) {
  const cookies = document.cookie.split(";").map((item) => item.trim());
  const cookie = cookies.find((item) => item.startsWith(name + "="));
  return cookie ? decodeURIComponent(cookie.split("=")[1]) : null;
}

const csrfToken = getCookie("csrftoken");

function updateTaskStatus(taskId, status) {
  const formData = new FormData();
  formData.append("task_id", taskId);
  formData.append("status", status);

  return fetch("/tasks/update-status/", {
    method: "POST",
    headers: {
      "X-CSRFToken": csrfToken,
    },
    body: formData,
  }).then((response) => response.json());
}

function createSortable(columnElement) {
  Sortable.create(columnElement, {
    group: "shared",
    animation: 150,
    onAdd: function (event) {
      const taskId = event.item.dataset.taskId;
      const status = columnElement.dataset.status;
      updateTaskStatus(taskId, status).then((data) => {
        if (!data.ok) {
          alert(data.error || "Unable to update task status.");
          event.from.appendChild(event.item);
        }
      });
    },
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".task-list").forEach((column) => createSortable(column));
});
