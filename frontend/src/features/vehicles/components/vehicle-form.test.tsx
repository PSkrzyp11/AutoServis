import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { VehicleForm } from "@/features/vehicles/components/vehicle-form";
import { EMPTY_VEHICLE_FORM } from "@/features/vehicles/schemas";
import { renderWithProviders } from "@/test/render-with-providers";

function renderForm(onSubmit = vi.fn()) {
  renderWithProviders(
    <VehicleForm
      idPrefix="test"
      defaultValues={EMPTY_VEHICLE_FORM}
      isPending={false}
      error={null}
      onSubmit={onSubmit}
      onCancel={vi.fn()}
    />,
  );
  return onSubmit;
}

describe("VehicleForm", () => {
  it("shows Polish validation errors and does not submit invalid data", async () => {
    const onSubmit = renderForm();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("VIN (opcjonalnie)"), "123");
    await user.click(screen.getByRole("button", { name: "Zapisz zmiany" }));

    expect(
      await screen.findByText("VIN musi mieć 17 znaków i nie może zawierać liter I, O ani Q."),
    ).toBeInTheDocument();
    expect(screen.getAllByText("To pole jest wymagane.").length).toBeGreaterThanOrEqual(2);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits a normalized payload", async () => {
    const onSubmit = renderForm();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Marka"), "Toyota");
    await user.type(screen.getByLabelText("Model"), "Corolla");
    await user.type(screen.getByLabelText("Rok produkcji"), "2019");
    await user.type(screen.getByLabelText("Numer rejestracyjny"), "wa 58213");
    await user.type(screen.getByLabelText("Przebieg w km (opcjonalnie)"), "87400");
    await user.click(screen.getByRole("button", { name: "Zapisz zmiany" }));

    await vi.waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith({
      make: "Toyota",
      model: "Corolla",
      production_year: 2019,
      plate_number: "WA58213",
      vin: null,
      mileage_km: 87400,
      engine: null,
    });
  });
});
