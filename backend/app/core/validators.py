@@
-from app.core.config import settings
+def is_student_email(email: str) -> bool:
+    # Import settings lazily to avoid import cycles during module import time.
+    from app.core.config import settings
+
+    _, _, domain = email.strip().lower().partition("@")
+    if not domain:
+        return False
+    return any(
+        domain == allowed or domain.endswith("." + allowed)
+        for allowed in settings.STUDENT_EMAIL_DOMAINS
+    )
+ 
+ 
+