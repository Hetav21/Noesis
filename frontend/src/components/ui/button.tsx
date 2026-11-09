import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center font-medium transition-[background-color,border-color,color,transform,opacity] duration-150 ease-out focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-zinc-400 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer active:scale-[0.98] select-none rounded-xl whitespace-nowrap",
  {
    variants: {
      variant: {
        default:
          "bg-zinc-100 hover:bg-white text-zinc-950 shadow-sm border border-white/30",
        primary:
          "bg-zinc-100 hover:bg-white text-zinc-950 shadow-sm border border-white/30",
        secondary:
          "bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-white/[0.08]",
        destructive:
          "bg-red-950/40 hover:bg-red-950/70 text-red-300 border border-red-500/20",
        danger:
          "bg-red-950/40 hover:bg-red-950/70 text-red-300 border border-red-500/20",
        outline:
          "bg-transparent hover:bg-white/[0.05] text-zinc-300 border border-white/[0.12] hover:text-white",
        ghost:
          "bg-transparent hover:bg-white/[0.06] text-zinc-400 hover:text-zinc-100",
        link: "text-zinc-300 underline-offset-4 hover:underline",
      },
      size: {
        default: "text-sm px-3.5 py-2 rounded-xl gap-2",
        md: "text-sm px-3.5 py-2 rounded-xl gap-2",
        sm: "text-xs px-2.5 py-1.5 rounded-lg gap-1.5",
        lg: "text-sm sm:text-base px-5 py-2.5 rounded-xl gap-2.5",
        icon: "h-8 w-8 p-0 rounded-lg",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      isLoading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref,
  ) => {
    const Comp = asChild ? Slot : "button";

    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0 text-current" />
        ) : (
          leftIcon
        )}
        {children}
        {!isLoading && rightIcon}
      </Comp>
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
