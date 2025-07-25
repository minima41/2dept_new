import { HTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning'
}

export const Badge = forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = 'primary', ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={clsx(
          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
          {
            'bg-blue-100 text-blue-800': variant === 'primary',
            'bg-gray-100 text-gray-800': variant === 'secondary',
            'bg-green-100 text-green-800': variant === 'success',
            'bg-red-100 text-red-800': variant === 'danger',
            'bg-yellow-100 text-yellow-800': variant === 'warning',
          },
          className
        )}
        {...props}
      />
    )
  }
)

Badge.displayName = 'Badge'