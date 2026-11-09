import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium tracking-normal transition-colors select-none',
  {
    variants: {
      variant: {
        default:
          'bg-zinc-800 text-zinc-200 border border-white/[0.08]',
        secondary:
          'bg-zinc-900/80 text-zinc-400 border border-white/[0.06]',
        neutral:
          'bg-zinc-900/80 text-zinc-400 border border-white/[0.06]',
        destructive:
          'bg-rose-500/10 text-rose-400 border border-rose-500/20',
        danger:
          'bg-rose-500/10 text-rose-400 border border-rose-500/20',
        outline:
          'text-zinc-300 border border-white/[0.12] bg-transparent',
        success:
          'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
        warning:
          'bg-amber-500/10 text-amber-400 border border-amber-500/20',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean;
  pulse?: boolean;
}

const dotColors: Record<string, string> = {
  default: 'bg-zinc-400',
  secondary: 'bg-zinc-500',
  neutral: 'bg-zinc-500',
  success: 'bg-emerald-400',
  warning: 'bg-amber-400',
  destructive: 'bg-rose-400',
  danger: 'bg-rose-400',
  outline: 'bg-zinc-400',
};

function Badge({
  className,
  variant = 'default',
  dot = false,
  pulse = false,
  children,
  ...props
}: BadgeProps) {
  const variantKey = variant || 'default';
  const dotColor = dotColors[variantKey] || 'bg-zinc-400';

  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot && (
        <span className="relative flex h-1.5 w-1.5 shrink-0">
          {pulse && (
            <span
              className={cn(
                'animate-ping absolute inline-flex h-full w-full rounded-full opacity-60',
                dotColor
              )}
            />
          )}
          <span
            className={cn('relative inline-flex rounded-full h-1.5 w-1.5', dotColor)}
          />
        </span>
      )}
      <span>{children}</span>
    </div>
  );
}

export { Badge, badgeVariants };
