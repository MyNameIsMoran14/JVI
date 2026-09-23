import { Badge, Card, Group, SimpleGrid, Stack, Text, UnstyledButton } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { api } from "../api/client";
import type { LabSeries, LatestLabValue } from "../api/types";

const FLAG_COLOR: Record<string, string> = { L: "blue", H: "red", N: "green" };
const FLAG_LABEL: Record<string, string> = { L: "ниже нормы", H: "выше нормы", N: "норма" };

export function Dashboard() {
  const [selected, setSelected] = useState<string | null>(null);

  const latest = useQuery({
    queryKey: ["labs", "latest"],
    queryFn: () => api.get<LatestLabValue[]>("/labs/latest"),
  });

  const activeCode = selected ?? latest.data?.[0]?.code ?? null;

  const series = useQuery({
    queryKey: ["labs", "series", activeCode],
    queryFn: () => api.get<LabSeries[]>(`/labs/series?codes=${activeCode}`),
    enabled: !!activeCode,
  });

  if (latest.isLoading) return <Text c="dimmed">Загрузка…</Text>;

  if (!latest.data?.length) {
    return (
      <Text c="dimmed">
        Пока нет подтверждённых анализов с ключевыми показателями — как только появятся, здесь будут
        карточки и графики.
      </Text>
    );
  }

  const chart = series.data?.[0];

  return (
    <Stack gap="lg">
      <SimpleGrid cols={2} spacing="sm">
        {latest.data.map((item) => (
          <UnstyledButton key={item.code} onClick={() => setSelected(item.code)}>
            <Card withBorder shadow="none" p="sm" bg={activeCode === item.code ? "var(--mantine-color-blue-light)" : undefined}>
              <Text size="xs" c="dimmed" lineClamp={1}>
                {item.name_ru}
              </Text>
              <Group gap={6} align="baseline">
                <Text fw={700} size="lg">
                  {item.value ?? item.value_text ?? "—"}
                </Text>
                {item.unit && (
                  <Text size="xs" c="dimmed">
                    {item.unit}
                  </Text>
                )}
              </Group>
              <Group gap={6}>
                {item.flag && (
                  <Badge color={FLAG_COLOR[item.flag]} size="xs" variant="light">
                    {FLAG_LABEL[item.flag]}
                  </Badge>
                )}
                {item.change_pct != null && (
                  <Text size="xs" c={item.change_pct > 0 ? "red" : "blue"}>
                    {item.change_pct > 0 ? "↑" : "↓"} {Math.abs(Math.round(item.change_pct))}%
                  </Text>
                )}
              </Group>
            </Card>
          </UnstyledButton>
        ))}
      </SimpleGrid>

      {chart && chart.points.length > 1 && (
        <Card withBorder shadow="none" p="sm">
          <Text fw={600} mb="sm">
            {chart.name_ru}
          </Text>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chart.points}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="taken_at" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke="#228be6" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}
    </Stack>
  );
}
