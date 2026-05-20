document.addEventListener("DOMContentLoaded", function () {
  const seatButtons = document.querySelectorAll(".available-seat");

  const selectedSeatsContainer =
    document.getElementById("selected-seats");

  const totalPriceElement =
    document.getElementById("total-price");

  const ticketPriceElement =
    document.getElementById("ticket-price");

  const selectedSeatIdsInput =
    document.getElementById("selected-seat-ids");

  let selectedSeats = [];
  let selectedSeatIds = [];

  function formatVND(value) {
    return new Intl.NumberFormat("vi-VN").format(value) + "đ";
  }

  function updateSummary() {
    selectedSeatsContainer.innerHTML = "";

    selectedSeats.forEach((seatName) => {
      const span = document.createElement("span");

      span.className =
        "bg-primary-container/20 text-on-primary-container px-md py-1 rounded-lg border border-primary-container/30 font-bold";

      span.textContent = seatName;

      selectedSeatsContainer.appendChild(span);
    });

    const pricePerSeat =
      seatButtons.length > 0
        ? Number(seatButtons[0].dataset.price)
        : 0;

    const total = selectedSeats.length * pricePerSeat;

    ticketPriceElement.textContent =
      formatVND(pricePerSeat) + " x " + selectedSeats.length;

    totalPriceElement.textContent =
      formatVND(total);

    selectedSeatIdsInput.value =
      selectedSeatIds.join(",");
  }

  seatButtons.forEach((button) => {
    button.addEventListener("click", function () {

      const seatId = this.dataset.seatId;
      const seatName = this.dataset.seatName;

      if (selectedSeatIds.includes(seatId)) {

        selectedSeatIds =
          selectedSeatIds.filter(
            (id) => id !== seatId
          );

        selectedSeats =
          selectedSeats.filter(
            (name) => name !== seatName
          );

        this.classList.remove(
          "bg-primary-container",
          "text-on-primary-container",
          "shadow-md"
        );

        this.classList.add(
          "border-2",
          "border-sky-400",
          "bg-white",
          "text-sky-600"
        );

      } else {

        selectedSeatIds.push(seatId);
        selectedSeats.push(seatName);

        this.classList.remove(
          "border-2",
          "border-sky-400",
          "bg-white",
          "text-sky-600"
        );

        this.classList.add(
          "bg-primary-container",
          "text-on-primary-container",
          "shadow-md"
        );
      }

      updateSummary();
    });
  });

  updateSummary();
});