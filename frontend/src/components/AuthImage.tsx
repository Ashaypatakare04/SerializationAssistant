"use client";

import React, { useEffect, useState } from "react";
import { api } from "../lib/api";

interface AuthImageProps extends Omit<React.ImgHTMLAttributes<HTMLImageElement>, "src"> {
  storageKey: string;
}

export const AuthImage = React.forwardRef<HTMLImageElement, AuthImageProps>(
  ({ storageKey, alt = "", ...props }, ref) => {
    const [objectUrl, setObjectUrl] = useState<string>("");
    const [hasError, setHasError] = useState<boolean>(false);

    useEffect(() => {
      if (!storageKey) {
        setObjectUrl("");
        return;
      }

      if (storageKey.startsWith("http")) {
        setObjectUrl(storageKey);
        return;
      }

      let active = true;
      let createdUrl = "";

      api
        .fetchStorageBlob(storageKey)
        .then((blob) => {
          if (!active) return;
          createdUrl = URL.createObjectURL(blob);
          setObjectUrl(createdUrl);
          setHasError(false);
        })
        .catch(() => {
          if (active) setHasError(true);
        });

      return () => {
        active = false;
        if (createdUrl) {
          URL.revokeObjectURL(createdUrl);
        }
      };
    }, [storageKey]);

    if (hasError || !objectUrl) {
      return null;
    }

    return (
      /* eslint-disable-next-line @next/next/no-img-element */
      <img ref={ref} src={objectUrl} alt={alt} {...props} />
    );
  }
);

AuthImage.displayName = "AuthImage";
