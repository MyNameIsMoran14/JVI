import { Box, Group, Stack, Text, UnstyledButton } from "@mantine/core";
import type { ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const TABS = [
  { path: "/", label: "Дашборд", icon: "📊" },
  { path: "/documents", label: "Документы", icon: "📄" },
  { path: "/visits", label: "Визиты", icon: "🩺" },
  { path: "/patient", label: "Карточка", icon: "👤" },
];

export function Layout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  return (
    <Stack h="100vh" gap={0}>
      <Box style={{ flex: 1, overflowY: "auto" }} p="md" pb={80}>
        {children}
      </Box>
      <Group
        gap={0}
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          borderTop: "1px solid var(--mantine-color-default-border)",
          background: "var(--mantine-color-body)",
        }}
      >
        {TABS.map((tab) => (
          <UnstyledButton
            key={tab.path}
            onClick={() => navigate(tab.path)}
            style={{ flex: 1, textAlign: "center", padding: "10px 0" }}
          >
            <Stack gap={2} align="center">
              <Text size="lg">{tab.icon}</Text>
              <Text size="xs" fw={pathname === tab.path ? 700 : 400}>
                {tab.label}
              </Text>
            </Stack>
          </UnstyledButton>
        ))}
      </Group>
    </Stack>
  );
}
