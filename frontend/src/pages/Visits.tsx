import { Button, Card, Divider, Group, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { useDisclosure } from "@mantine/hooks";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api/client";
import type { TreatmentCreate, TreatmentRead, VisitCreate, VisitRead } from "../api/types";

function toIsoDate(date: Date | null): string | null {
  if (!date) return null;
  return date.toISOString().slice(0, 10);
}

export function Visits() {
  const queryClient = useQueryClient();
  const [formOpened, { toggle: toggleForm, close: closeForm }] = useDisclosure(false);

  const visits = useQuery({ queryKey: ["visits"], queryFn: () => api.get<VisitRead[]>("/visits") });
  const treatments = useQuery({
    queryKey: ["treatments"],
    queryFn: () => api.get<TreatmentRead[]>("/treatments"),
  });

  const [date, setDate] = useState<Date | null>(new Date());
  const [doctor, setDoctor] = useState("");
  const [clinic, setClinic] = useState("");
  const [summary, setSummary] = useState("");
  const [decisions, setDecisions] = useState("");
  const [nextVisitDate, setNextVisitDate] = useState<Date | null>(null);

  const createVisit = useMutation({
    mutationFn: (body: VisitCreate) => api.post<VisitRead>("/visits", body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["visits"] });
      setDoctor("");
      setClinic("");
      setSummary("");
      setDecisions("");
      setNextVisitDate(null);
      closeForm();
    },
  });

  const [treatmentFormOpened, { toggle: toggleTreatmentForm, close: closeTreatmentForm }] = useDisclosure(false);
  const [regimen, setRegimen] = useState("");
  const [cycleNo, setCycleNo] = useState("");
  const [startDate, setStartDate] = useState<Date | null>(new Date());

  const createTreatment = useMutation({
    mutationFn: (body: TreatmentCreate) => api.post<TreatmentRead>("/treatments", body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["treatments"] });
      setRegimen("");
      setCycleNo("");
      closeTreatmentForm();
    },
  });

  function submitVisit() {
    const isoDate = toIsoDate(date);
    if (!isoDate) return;
    createVisit.mutate({
      date: isoDate,
      doctor: doctor || null,
      clinic: clinic || null,
      summary: summary || null,
      decisions: decisions || null,
      next_visit_date: toIsoDate(nextVisitDate),
    });
  }

  function submitTreatment() {
    const isoStart = toIsoDate(startDate);
    if (!isoStart || !regimen) return;
    createTreatment.mutate({
      regimen,
      cycle_no: cycleNo ? Number(cycleNo) : null,
      start_date: isoStart,
      end_date: null,
      notes: null,
    });
  }

  return (
    <Stack gap="lg">
      <Stack gap="sm">
        <Group justify="space-between">
          <Text fw={700}>Визиты</Text>
          <Button size="xs" variant="light" onClick={toggleForm}>
            {formOpened ? "Отмена" : "+ Добавить"}
          </Button>
        </Group>

        {formOpened && (
          <Card withBorder shadow="none" p="sm">
            <Stack gap="xs">
              <DateInput label="Дата" value={date} onChange={setDate} valueFormat="DD.MM.YYYY" />
              <TextInput label="Врач" value={doctor} onChange={(e) => setDoctor(e.currentTarget.value)} />
              <TextInput label="Клиника" value={clinic} onChange={(e) => setClinic(e.currentTarget.value)} />
              <Textarea label="Заметки" value={summary} onChange={(e) => setSummary(e.currentTarget.value)} autosize />
              <Textarea
                label="Назначения"
                value={decisions}
                onChange={(e) => setDecisions(e.currentTarget.value)}
                autosize
              />
              <DateInput
                label="Следующий визит"
                value={nextVisitDate}
                onChange={setNextVisitDate}
                valueFormat="DD.MM.YYYY"
                clearable
              />
              <Button onClick={submitVisit} loading={createVisit.isPending} disabled={!date}>
                Сохранить
              </Button>
            </Stack>
          </Card>
        )}

        {visits.data?.length ? (
          visits.data.map((v) => (
            <Card key={v.id} withBorder shadow="none" p="sm">
              <Text fw={600}>{new Date(v.date).toLocaleDateString("ru-RU")}</Text>
              {v.doctor && <Text size="sm">{v.doctor}{v.clinic ? `, ${v.clinic}` : ""}</Text>}
              {v.summary && <Text size="sm" c="dimmed">{v.summary}</Text>}
              {v.decisions && <Text size="sm">Назначения: {v.decisions}</Text>}
              {v.next_visit_date && (
                <Text size="xs" c="dimmed">
                  Следующий визит: {new Date(v.next_visit_date).toLocaleDateString("ru-RU")}
                </Text>
              )}
            </Card>
          ))
        ) : (
          <Text c="dimmed" size="sm">Визитов пока нет.</Text>
        )}
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Group justify="space-between">
          <Text fw={700}>Лечение</Text>
          <Button size="xs" variant="light" onClick={toggleTreatmentForm}>
            {treatmentFormOpened ? "Отмена" : "+ Добавить"}
          </Button>
        </Group>

        {treatmentFormOpened && (
          <Card withBorder shadow="none" p="sm">
            <Stack gap="xs">
              <TextInput label="Схема" value={regimen} onChange={(e) => setRegimen(e.currentTarget.value)} />
              <TextInput label="Цикл №" value={cycleNo} onChange={(e) => setCycleNo(e.currentTarget.value)} />
              <DateInput label="Начало" value={startDate} onChange={setStartDate} valueFormat="DD.MM.YYYY" />
              <Button onClick={submitTreatment} loading={createTreatment.isPending} disabled={!regimen || !startDate}>
                Сохранить
              </Button>
            </Stack>
          </Card>
        )}

        {treatments.data?.length ? (
          treatments.data.map((t) => (
            <Card key={t.id} withBorder shadow="none" p="sm">
              <Text fw={600}>
                {t.regimen}
                {t.cycle_no ? `, цикл ${t.cycle_no}` : ""}
              </Text>
              <Text size="xs" c="dimmed">
                с {new Date(t.start_date).toLocaleDateString("ru-RU")}
                {t.end_date ? ` по ${new Date(t.end_date).toLocaleDateString("ru-RU")}` : ""}
              </Text>
            </Card>
          ))
        ) : (
          <Text c="dimmed" size="sm">Лечение пока не указано.</Text>
        )}
      </Stack>
    </Stack>
  );
}
