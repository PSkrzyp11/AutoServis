"use client";

import { CarIcon, PlusIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { ConfirmButton } from "@/components/confirm-button";
import { PageHeader } from "@/components/page-header";
import { StatusMessage } from "@/components/status-message";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  useCreateVehicle,
  useDeleteVehicle,
  useUpdateVehicle,
  useVehicles,
} from "@/features/vehicles/api";
import { VehicleForm } from "@/features/vehicles/components/vehicle-form";
import { EMPTY_VEHICLE_FORM, toVehicleFormValues } from "@/features/vehicles/schemas";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import type { Vehicle } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";

type Notice = "saved" | "deleted" | null;

function vehicleName(vehicle: Vehicle): string {
  return `${vehicle.make} ${vehicle.model}`;
}

function VehicleDetails({ vehicle }: { vehicle: Vehicle }) {
  const t = useTranslations("vehicles");
  const notProvided = useTranslations("common")("notProvided");
  return (
    <dl className="grid gap-2 text-sm sm:grid-cols-2">
      <div>
        <dt className="text-muted-foreground">{t("details.plateNumber")}</dt>
        <dd className="font-mono">{vehicle.plate_number}</dd>
      </div>
      <div>
        <dt className="text-muted-foreground">{t("details.vin")}</dt>
        <dd className="font-mono break-all">{vehicle.vin ?? notProvided}</dd>
      </div>
      <div>
        <dt className="text-muted-foreground">{t("details.mileage")}</dt>
        <dd>
          {vehicle.mileage_km === null
            ? notProvided
            : t("mileageValue", { mileage: formatNumber(vehicle.mileage_km) })}
        </dd>
      </div>
      <div>
        <dt className="text-muted-foreground">{t("details.engine")}</dt>
        <dd>{vehicle.engine ?? notProvided}</dd>
      </div>
    </dl>
  );
}

function VehicleCard({
  vehicle,
  onSaved,
  onDeleted,
}: {
  vehicle: Vehicle;
  onSaved: () => void;
  onDeleted: () => void;
}) {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const [isEditing, setIsEditing] = useState(false);
  const updateVehicle = useUpdateVehicle();
  const deleteVehicle = useDeleteVehicle();

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <CarIcon aria-hidden="true" className="size-5" />
            {vehicleName(vehicle)}{" "}
            <span className="font-normal text-muted-foreground">({vehicle.production_year})</span>
          </h2>
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4">
        {isEditing ? (
          <VehicleForm
            idPrefix={`vehicle-${vehicle.id}`}
            defaultValues={toVehicleFormValues(vehicle)}
            isPending={updateVehicle.isPending}
            error={updateVehicle.error}
            onCancel={() => setIsEditing(false)}
            onSubmit={(payload) =>
              updateVehicle.mutate(
                { vehicleId: vehicle.id, payload },
                {
                  onSuccess: () => {
                    setIsEditing(false);
                    onSaved();
                  },
                },
              )
            }
          />
        ) : (
          <>
            <VehicleDetails vehicle={vehicle} />
            {deleteVehicle.isError ? (
              <StatusMessage tone="error" message={errorMessage(deleteVehicle.error)} />
            ) : null}
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
                {t("common.edit")}
              </Button>
              <ConfirmButton
                label={t("common.delete")}
                question={t("vehicles.deleteQuestion", { name: vehicleName(vehicle) })}
                disabled={deleteVehicle.isPending}
                onConfirm={() => deleteVehicle.mutate(vehicle.id, { onSuccess: onDeleted })}
              />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export function VehiclesView() {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const vehicles = useVehicles();
  const createVehicle = useCreateVehicle();
  const [isAdding, setIsAdding] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  return (
    <div className="grid gap-6">
      <PageHeader
        title={t("vehicles.title")}
        description={t("vehicles.description")}
        actions={
          isAdding ? null : (
            <Button
              onClick={() => {
                setNotice(null);
                setIsAdding(true);
              }}
            >
              <PlusIcon aria-hidden="true" />
              {t("vehicles.add")}
            </Button>
          )
        }
      />

      {notice ? <StatusMessage tone="success" message={t(`vehicles.${notice}`)} /> : null}

      {isAdding ? (
        <Card>
          <CardHeader>
            <CardTitle>
              <h2 className="text-lg font-semibold">{t("vehicles.formTitleAdd")}</h2>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <VehicleForm
              idPrefix="new-vehicle"
              defaultValues={EMPTY_VEHICLE_FORM}
              isPending={createVehicle.isPending}
              error={createVehicle.error}
              onCancel={() => setIsAdding(false)}
              onSubmit={(payload) =>
                createVehicle.mutate(payload, {
                  onSuccess: () => {
                    setIsAdding(false);
                    setNotice("saved");
                  },
                })
              }
            />
          </CardContent>
        </Card>
      ) : null}

      {vehicles.isError ? (
        <StatusMessage tone="error" message={errorMessage(vehicles.error)} />
      ) : null}
      {vehicles.isPending ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("common.loading")}
        </p>
      ) : null}
      {vehicles.data?.items.length === 0 && !isAdding ? (
        <p className="text-muted-foreground">{t("vehicles.empty")}</p>
      ) : null}
      {vehicles.data && vehicles.data.items.length > 0 ? (
        <ul className="grid gap-4 lg:grid-cols-2" aria-label={t("vehicles.listLabel")}>
          {vehicles.data.items.map((vehicle) => (
            <li key={vehicle.id}>
              <VehicleCard
                vehicle={vehicle}
                onSaved={() => setNotice("saved")}
                onDeleted={() => setNotice("deleted")}
              />
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
