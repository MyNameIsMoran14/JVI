import { Badge, Button, Card, Group, Modal, Stack, Table, Text } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api/client";
import type { DocumentRead, LabResultRead } from "../api/types";

const STATUS_LABEL: Record<DocumentRead["status"], string> = {
  uploaded: "загружен",
  parsing: "распознаётся",
  needs_review: "нужна проверка",
  confirmed: "подтверждён",
  failed: "ошибка",
};

const STATUS_COLOR: Record<DocumentRead["status"], string> = {
  uploaded: "gray",
  parsing: "blue",
  needs_review: "orange",
  confirmed: "green",
  failed: "red",
};

const KIND_LABEL: Record<DocumentRead["kind"], string> = {
  lab: "Анализы",
  discharge: "Выписка",
  imaging: "Снимок",
  other: "Другое",
};

export function Documents() {
  const [opened, { open, close }] = useDisclosure(false);
  const [activeId, setActiveId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.get<DocumentRead[]>("/documents"),
  });

  const extraction = useQuery({
    queryKey: ["documents", activeId, "extraction"],
    queryFn: () => api.get<LabResultRead[]>(`/documents/${activeId}/extraction`),
    enabled: activeId != null,
  });

  const confirmMutation = useMutation({
    mutationFn: () => api.post(`/documents/${activeId}/confirm`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      void queryClient.invalidateQueries({ queryKey: ["labs"] });
      close();
    },
  });

  const discardMutation = useMutation({
    mutationFn: () => api.post(`/documents/${activeId}/discard`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      close();
    },
  });

  function openDocument(doc: DocumentRead) {
    setActiveId(doc.id);
    open();
  }

  if (documents.isLoading) return <Text c="dimmed">Загрузка…</Text>;

  return (
    <Stack gap="sm">
      {!documents.data?.length && <Text c="dimmed">Файлов пока нет — пришлите их боту.</Text>}
      {documents.data?.map((doc) => (
        <Card key={doc.id} withBorder shadow="none" p="sm" onClick={() => openDocument(doc)} style={{ cursor: "pointer" }}>
          <Group justify="space-between">
            <Stack gap={2}>
              <Text fw={600}>{KIND_LABEL[doc.kind]}</Text>
              <Text size="xs" c="dimmed">
                {doc.taken_at ?? new Date(doc.created_at).toLocaleDateString("ru-RU")}
                {doc.lab_name ? ` · ${doc.lab_name}` : ""}
              </Text>
            </Stack>
            <Badge color={STATUS_COLOR[doc.status]} variant="light">
              {STATUS_LABEL[doc.status]}
            </Badge>
          </Group>
        </Card>
      ))}

      <Modal opened={opened} onClose={close} title="Показатели файла" size="md">
        {extraction.isLoading && <Text c="dimmed">Загрузка…</Text>}
        {extraction.data && (
          <Stack gap="sm">
            <Table>
              <Table.Tbody>
                {extraction.data.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>{r.analyte_name}</Table.Td>
                    <Table.Td>
                      {r.value ?? r.value_text ?? "—"} {r.unit ?? ""}
                    </Table.Td>
                    <Table.Td>
                      {r.flag && (
                        <Badge size="xs" color={r.flag === "N" ? "green" : "red"} variant="light">
                          {r.flag}
                        </Badge>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            {extraction.data.some((r) => !r.confirmed) && (
              <Group grow>
                <Button color="green" onClick={() => confirmMutation.mutate()} loading={confirmMutation.isPending}>
                  ✅ Всё верно
                </Button>
                <Button color="red" variant="light" onClick={() => discardMutation.mutate()} loading={discardMutation.isPending}>
                  🗑 Не сохранять
                </Button>
              </Group>
            )}
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
