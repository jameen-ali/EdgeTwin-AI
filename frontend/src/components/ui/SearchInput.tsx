// ─── SearchInput Component ────────────────────────────────────────────────────
import { useState, useEffect } from 'react';
import { Search, X } from 'lucide-react';
import { clsx } from 'clsx';
import { Input } from './Input';

export interface SearchInputProps {
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  debounceMs?: number;
  className?: string;
}

export function SearchInput({
  placeholder = 'Search...',
  value = '',
  onChange,
  debounceMs = 300,
  className,
}: SearchInputProps) {
  const [localValue, setLocalValue] = useState(value);

  // Sync external value
  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  // Debounce internal value changes to external onChange
  useEffect(() => {
    if (!onChange) return;
    const timer = setTimeout(() => onChange(localValue), debounceMs);
    return () => clearTimeout(timer);
  }, [localValue, onChange, debounceMs]);

  return (
    <div className={clsx('relative', className)}>
      <Input
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        placeholder={placeholder}
        icon={<Search className="h-4 w-4" />}
        className={localValue ? 'pr-8' : ''}
      />
      {localValue && (
        <button
          type="button"
          onClick={() => {
            setLocalValue('');
            onChange?.('');
          }}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus:outline-none"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
