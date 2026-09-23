import { Button, NumberInput, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { PatientRead, PatientUpdate } from "../api/types";

function listToText(items: string[]): string {
  return items.join(", ");
}

function textToList(text: string): string[] {
  return text
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function PatientCard() {
  const queryClient = useQueryClient();
  const patient = useQuery({ queryKey: ["patient"], queryFn: () => api.get<PatientRead>("/patient") });

  const [form, setForm] = useState<PatientUpdate | null>(null);

  useEffect(() => {
    if (patient.data) {
      setForm({
        full_name: patient.data.full_name,
        birth_year: patient.data.birth_year,
        diagnosis: patient.data.diagnosis,
        stage: patient.data.stage,
        paraprotein_type: patient.data.paraprotein_type,
        comorbidities: patient.data.comorbidities,
        allergies: patient.data.allergies,
        notes: patient.data.notes,
      });
    }
  }, [patient.data]);

  const save = useMutation({
    mutationFn: (body: PatientUpdate) => api.patch<PatientRead>("/patient", body),
    onSuccess: (updated) => queryClient.setQueryData(["patient"], updated),
  });

  if (patient.isLoading || !form) return <Text c="dimmed">Загрузка…</Text>;

  return (
    <Stack gap="sm">
      <TextInput
        label="ФИО"
        value={form.full_name ?? ""}
        onChange={(e) => setForm({ ...form, full_name: e.currentTarget.value })}
      />
      <NumberInput
        label="Год рождения"
        value={form.birth_year ?? undefined}
        onChange={(v) => setForm({ ...form, birth_year: typeof v === "number" ? v : null })}
        clampBehavior="strict"
        min={1900}
        max={new Date().getFullYear()}
      />
      <Textarea
        label="Диагноз"
        value={form.diagnosis ?? ""}
        onChange={(e) => setForm({ ...form, diagnosis: e.currentTarget.value })}
        autosize
      />
      <TextInput
        label="Стадия"
        value={form.stage ?? ""}
        onChange={(e) => setForm({ ...form, stage: e.currentTarget.value })}
      />
      <TextInput
        label="Тип парапротеина"
        value={form.paraprotein_type ?? ""}
        onChange={(e) => setForm({ ...form, paraprotein_type: e.currentTarget.value })}
      />
      <TextInput
        label="Сопутствующие заболевания (через запятую)"
        value={listToText(form.comorbidities ?? [])}
        onChange={(e) => setForm({ ...form, comorbidities: textToList(e.currentTarget.value) })}
      />
      <TextInput
        label="Аллергии (через запятую)"
        value={listToText(form.allergies ?? [])}
        onChange={(e) => setForm({ ...form, allergies: textToList(e.currentTarget.value) })}
      />
      <Textarea
        label="Заметки"
        value={form.notes ?? ""}
        onChange={(e) => setForm({ ...form, notes: e.currentTarget.value })}
        autosize
      />
      <Button onClick={() => save.mutate(form)} loading={save.isPending}>
        Сохранить
      </Button>
      {save.isSuccess && (
        <Text c="green" size="sm">
          Сохранено
        </Text>
      )}
    </Stack>
  );
}
