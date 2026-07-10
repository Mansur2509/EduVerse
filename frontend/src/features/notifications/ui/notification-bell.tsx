"use client";

import { Bell } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import type { Notification } from "@/entities/notification";
import {
  getNotificationsRequest,
  markAllNotificationsReadRequest,
  updateNotificationStatusRequest
} from "@/features/notifications";
import { useI18n } from "@/shared/i18n";
import { formatDateTime } from "@/shared/lib/date-time";

const DROPDOWN_ITEM_LIMIT = 8;

export function NotificationBell() {
  const { locale, t } = useI18n();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await getNotificationsRequest({ status: "unread" });
      setNotifications(response.results.slice(0, DROPDOWN_ITEM_LIMIT));
    } catch {
      // A failed background fetch shouldn't break the shell chrome -- the
      // bell just keeps showing its last-known count until the next open.
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!isOpen) return;
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const toggleOpen = () => {
    setIsOpen((current) => {
      const next = !current;
      if (next) void load();
      return next;
    });
  };

  const handleItemClick = async (notification: Notification) => {
    setNotifications((current) => current.filter((item) => item.id !== notification.id));
    setIsOpen(false);
    try {
      await updateNotificationStatusRequest(notification.id, "read");
    } catch {
      void load();
    }
  };

  const handleMarkAllRead = async () => {
    setNotifications([]);
    try {
      await markAllNotificationsReadRequest();
    } catch {
      void load();
    }
  };

  const unreadCount = notifications.length;

  return (
    <div className="relative" ref={containerRef}>
      <button
        aria-label={t("notifications.bell.ariaLabel")}
        className="relative grid size-9 place-items-center rounded-sm border text-muted-foreground transition-colors hover:border-primary/35 hover:text-foreground"
        onClick={toggleOpen}
        type="button"
      >
        <Bell aria-hidden className="size-4" />
        {unreadCount > 0 ? (
          <span className="absolute -right-1 -top-1 flex size-4 items-center justify-center rounded-full bg-danger text-[0.6rem] font-bold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <div className="absolute right-0 top-full z-40 mt-2 w-80 max-w-[90vw] rounded-sm border bg-card shadow-card">
          <div className="flex items-center justify-between gap-2 border-b px-3 py-2">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
              {t("notifications.bell.title")}
            </p>
            {unreadCount > 0 ? (
              <button
                className="text-xs font-semibold text-primary-hover hover:underline"
                onClick={() => void handleMarkAllRead()}
                type="button"
              >
                {t("notifications.bell.markAllRead")}
              </button>
            ) : null}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {isLoading ? (
              <p className="px-3 py-4 text-xs text-muted-foreground">{t("notifications.bell.loading")}</p>
            ) : notifications.length === 0 ? (
              <p className="px-3 py-4 text-xs text-muted-foreground">{t("notifications.bell.empty")}</p>
            ) : (
              <ul>
                {notifications.map((notification) => (
                  <li className="border-b last:border-b-0" key={notification.id}>
                    <Link
                      className="block px-3 py-2.5 hover:bg-elevated"
                      href={notification.action_url || "/notifications"}
                      onClick={() => void handleItemClick(notification)}
                    >
                      <p className="line-clamp-2 text-sm font-semibold leading-5">{notification.title}</p>
                      <p className="mt-1 text-[0.68rem] text-muted-foreground">
                        {formatDateTime(notification.created_at, locale)}
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <Link
            className="block border-t px-3 py-2 text-center text-xs font-semibold text-primary-hover hover:underline"
            href="/notifications"
            onClick={() => setIsOpen(false)}
          >
            {t("notifications.bell.viewAll")}
          </Link>
        </div>
      ) : null}
    </div>
  );
}
