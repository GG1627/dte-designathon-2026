import { Host, Picker } from '@expo/ui';
import { createElement } from 'react';
import { Platform, View } from 'react-native';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c, Spacing as s } from '@/constants/theme';

export function SelectionControl({ label, value, options, onChange }: {
  label: string; value: string; options: { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  const content = <>
    <Text type="label" themeColor="textSecondary">{label}</Text>
    <Host colorScheme="dark" seedColor={c.accent} matchContents style={{ minHeight: 48 }}>
      <Picker selectedValue={value} onValueChange={onChange}>
        {options.map((option) => <Picker.Item key={option.value} {...option} />)}
      </Picker>
    </Host>
  </>;
  return <View style={{ flexGrow: 1, flexShrink: 1, minWidth: 100, gap: s.two }}>
    {Platform.OS === 'web'
      ? createElement('label', { style: { display: 'flex', flexDirection: 'column', gap: 8 } }, content)
      : content}
  </View>;
}
