import { BottomSheet, Host, Switch } from '@expo/ui';
import { Link, router, type Href } from 'expo-router';
import { SymbolView, type SymbolViewProps } from 'expo-symbols';
import { useState, type ReactNode } from 'react';
import { Platform, Pressable, ScrollView, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Circle, Path } from 'react-native-svg';

import { ThemedText as Text } from '@/components/themed-text';
import { useDemo } from '@/components/demo-provider';
import {
  MaxContentWidth,
  Palette as c,
  Radius,
  Spacing as s,
} from '@/constants/theme';
import { devices, formatDate, type Joint, type Session } from '@/data/demo';

export function Icon({
  name,
  size = 20,
  color = c.accent,
}: {
  name: SymbolViewProps['name'];
  size?: number;
  color?: string;
}) {
  return (
    <View
      aria-hidden
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants">
      <SymbolView name={name} size={size} tintColor={color} />
    </View>
  );
}

export function Screen({ children }: { children: ReactNode }) {
  const insets = useSafeAreaInsets();
  return (
    <ScrollView
      contentInsetAdjustmentBehavior="automatic"
      style={{ flex: 1, backgroundColor: c.background }}
      contentContainerStyle={{
        alignItems: 'center',
        paddingBottom:
          Platform.OS === 'web' ? 112 : Math.max(insets.bottom, s.four),
      }}>
      <View
        style={{
          width: '100%',
          maxWidth: MaxContentWidth,
          padding: s.four,
          paddingTop: s.three,
          gap: s.five,
        }}>
        {children}
      </View>
    </ScrollView>
  );
}

export function Row({
  children,
  wrap = false,
}: {
  children: ReactNode;
  wrap?: boolean;
}) {
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: s.three,
        ...(wrap ? { flexWrap: 'wrap' as const } : {}),
      }}>
      {children}
    </View>
  );
}

export function Panel({
  children,
  accent = false,
}: {
  children: ReactNode;
  accent?: boolean;
}) {
  return (
    <View
      style={{
        padding: s.four,
        backgroundColor: c.backgroundElement,
        borderRadius: Radius.large,
        borderCurve: 'continuous',
        borderWidth: 1,
        borderColor: accent ? c.accentMuted : c.border,
        gap: s.three,
      }}>
      {children}
    </View>
  );
}

export function Badge({
  children,
  muted = false,
  comparison = false,
}: {
  children: string;
  muted?: boolean;
  comparison?: boolean;
}) {
  return (
    <View
      style={{
        paddingHorizontal: s.two,
        paddingVertical: s.one,
        backgroundColor: comparison
          ? c.comparisonMuted
          : muted
            ? c.backgroundSelected
            : c.accentMuted,
        borderRadius: Radius.small,
      }}>
      <Text
        type="small"
        style={{
          color: comparison ? c.comparison : muted ? c.textSecondary : c.accent,
        }}>
        {children}
      </Text>
    </View>
  );
}

export function Action({
  children,
  onPress,
  href,
  primary = false,
  label,
}: {
  children: string;
  onPress?: () => void;
  href?: Href;
  primary?: boolean;
  label?: string;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label ?? children}
      onPress={href ? () => router.push(href) : onPress}
      style={({ pressed }) => ({
        minHeight: 48,
        minWidth: 48,
        paddingHorizontal: primary ? s.three : 0,
        paddingVertical: s.two,
        borderRadius: Radius.medium,
        backgroundColor: primary ? c.accent : 'transparent',
        alignItems: 'center',
        justifyContent: 'center',
        opacity: pressed ? 0.65 : 1,
      })}>
      <Text
        type="smallBold"
        style={{ color: primary ? c.background : c.accent }}>
        {children}
      </Text>
    </Pressable>
  );
}

export function Section({
  title,
  action,
  children,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <View style={{ gap: s.three }}>
      <Row>
        <Text
          accessibilityRole="header"
          aria-level={2}
          type="subtitle"
          style={{ flexShrink: 1 }}>
          {title}
        </Text>
        {action}
      </Row>
      {children}
    </View>
  );
}

export function Divider() {
  return <View style={{ height: 1, backgroundColor: c.border }} />;
}

export function Sheet({
  title,
  open,
  onClose,
  children,
}: {
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <Host colorScheme="dark" style={{ position: 'absolute' }}>
      <BottomSheet
        isPresented={open}
        onDismiss={onClose}
        snapPoints={['half', 'full']}
        containerColor={c.backgroundElement}
        contentPadding={0}>
        <ScrollView
          contentContainerStyle={{
            padding: s.four,
            gap: s.three,
            paddingBottom: s.five,
          }}>
          <Row>
            <Text
              accessibilityRole="header"
              type="subtitle"
              style={{ flex: 1 }}>
              {title}
            </Text>
            <Action onPress={onClose}>Close</Action>
          </Row>
          {children}
        </ScrollView>
      </BottomSheet>
    </Host>
  );
}

export function DemoHeader({ label }: { label: string }) {
  return (
    <Row wrap>
      <Text type="small" themeColor="textSecondary">
        {label}
      </Text>
      <Badge muted>Demo data</Badge>
    </Row>
  );
}

export function PageIntro({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <View style={{ gap: s.two }}>
      <Row>
        <View
          style={{ flexDirection: 'row', alignItems: 'center', gap: s.two }}>
          <View
            aria-hidden
            accessibilityElementsHidden
            importantForAccessibility="no-hide-descendants">
            <Svg width={22} height={24} viewBox="0 0 22 24">
              <Path
                d="M5 3V21M6 12L18 3"
                stroke={c.text}
                strokeWidth={2.4}
                strokeLinecap="round"
              />
              <Path
                d="M6 12L18 21"
                stroke={c.accent}
                strokeWidth={2.4}
                strokeLinecap="round"
              />
              <Circle
                cx={6}
                cy={12}
                r={3.8}
                fill={c.background}
                stroke={c.accent}
                strokeWidth={1.5}
              />
            </Svg>
          </View>
          <Text type="label" style={{ color: c.accent }}>
            Kintra
          </Text>
        </View>
        <Badge muted>Demo data</Badge>
      </Row>
      <Text
        accessibilityRole="header"
        style={{
          fontSize: 36,
          lineHeight: 44,
          fontWeight: '700',
          letterSpacing: -1,
        }}>
        {title}
      </Text>
      <Text type="small" themeColor="textSecondary">
        {description}
      </Text>
    </View>
  );
}

export function Metric({
  label,
  value,
  unit,
  detail,
}: {
  label: string;
  value: string;
  unit?: string;
  detail: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`${label}: ${value} ${unit ?? ''}. Show explanation`}
        onPress={() => setOpen(true)}
        style={({ pressed }) => ({
          minHeight: 80,
          flexGrow: 1,
          flexBasis: '40%',
          gap: s.one,
          opacity: pressed ? 0.65 : 1,
        })}>
        <Text type="small" themeColor="textSecondary">
          {label}{' '}
          <Text type="small" style={{ color: c.accent }}>
            ↗
          </Text>
        </Text>
        <Text type="subtitle" style={{ fontVariant: ['tabular-nums'] }}>
          {value}
          {unit ? (
            <Text type="small" themeColor="textSecondary">
              {' '}
              {unit}
            </Text>
          ) : null}
        </Text>
      </Pressable>
      <Sheet title={label} open={open} onClose={() => setOpen(false)}>
        <Badge muted>Demo · derived metric</Badge>
        <Text>{detail}</Text>
      </Sheet>
    </>
  );
}

export function SessionRow({ session }: { session: Session }) {
  return (
    <Link
      href={{ pathname: '/session/[id]', params: { id: session.id } }}
      asChild>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`${session.activity}, ${session.minutes} minutes, ${formatDate(session.date)}. View session`}
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: 12,
          minHeight: 80,
          padding: s.three,
          backgroundColor: c.backgroundElement,
          borderRadius: Radius.medium,
          borderWidth: 1,
          borderColor: c.border,
        }}>
        <View
          style={{
            width: 40,
            height: 40,
            flexShrink: 0,
            borderRadius: Radius.medium,
            backgroundColor: c.accentMuted,
            alignItems: 'center',
            justifyContent: 'center',
          }}>
          <Icon
            name={{
              ios:
                session.activity === 'Running' ? 'figure.run' : 'figure.walk',
              android:
                session.activity === 'Running'
                  ? 'directions_run'
                  : 'directions_walk',
              web:
                session.activity === 'Running'
                  ? 'directions_run'
                  : 'directions_walk',
            }}
          />
        </View>
        <View style={{ flex: 1, minWidth: 0, gap: s.one }}>
          <Text type="smallBold">{session.activity}</Text>
          <Text type="small" themeColor="textSecondary">
            {session.offset === 0 ? 'Today' : formatDate(session.date)} ·{' '}
            {session.coverage}% coverage
          </Text>
        </View>
        <Text type="smallBold" style={{ flexShrink: 0, fontVariant: ['tabular-nums'] }}>{session.minutes} min</Text>
        <Icon
          name={{
            ios: 'chevron.right',
            android: 'chevron_right',
            web: 'chevron_right',
          }}
          size={16}
          color={c.textSecondary}
        />
      </Pressable>
    </Link>
  );
}

export function DeviceSheet({
  joint,
  open,
  onClose,
}: {
  joint?: Joint;
  open: boolean;
  onClose: () => void;
}) {
  const { online, setOnline, placementChecked, checkPlacement } = useDemo();
  const shownDevices = joint
    ? devices.filter((device) => joint.devices.includes(device.id))
    : devices;
  return (
    <Sheet
      title={joint ? `${joint.name} setup` : 'Device status'}
      open={open}
      onClose={onClose}>
      <Badge muted>Demo devices</Badge>
      <Text type="small" themeColor="textSecondary">
        Connection switches simulate device status. Bluetooth is not connected
        in this prototype.
      </Text>
      {shownDevices.length ? (
        shownDevices.map((device) => (
          <View key={device.id} style={{ gap: s.two }}>
            <Row wrap>
              <Text type="smallBold">
                {device.name} · {device.placement}
              </Text>
              <Text type="small" themeColor="textSecondary">
                {device.battery}% battery
              </Text>
            </Row>
            <Host colorScheme="dark" matchContents style={{ minHeight: 48 }}>
              <Switch
                label={`Simulate ${device.name} connected`}
                value={online[device.id]}
                onValueChange={(value) => setOnline(device.id, value)}
              />
            </Host>
            <Divider />
          </View>
        ))
      ) : (
        <Text>
          No devices assigned. This joint has no recorded measurements.
        </Text>
      )}
      {joint ? (
        <>
          <Text type="smallBold">Placement checklist</Text>
          {joint.placement.map((step, index) => (
            <Text key={step} type="small" themeColor="textSecondary">
              {index + 1}. {step}
            </Text>
          ))}
          {joint.monitored ? (
            <>
              {placementChecked.includes(joint.id) ? (
                <Badge>Placement checklist confirmed</Badge>
              ) : (
                <Action primary onPress={() => checkPlacement(joint.id)}>
                  Confirm placement checklist
                </Action>
              )}
              <Text type="small" themeColor="textSecondary">
                Checklist confirmation is saved for this preview. Sensor
                calibration still requires real hardware.
              </Text>
            </>
          ) : null}
        </>
      ) : (
        <Text type="small" themeColor="textSecondary">
          Pod 02 is shared by the knee and ankle configurations. A disconnected
          shared pod affects both joints.
        </Text>
      )}
    </Sheet>
  );
}
