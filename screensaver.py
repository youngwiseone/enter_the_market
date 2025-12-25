"""
screensaver.py
---------------

This module implements a simple screensaver for the market game.  When the
player has selected a screensaver in the Store and the application has
been idle for a configurable period of time, a translucent overlay will
appear over the screen and a randomly chosen item icon will bounce around
the window.  Movement stops and the overlay disappears as soon as the
player interacts with the mouse or keyboard.

The screensaver has two primary components:

* ``BouncingItem`` handles the motion and drawing of a single icon.  When
  activated it chooses a random image from the provided items catalogue
  and begins moving it at a fixed velocity.  The image will bounce off
  the edges of the given bounding rectangle.  A semi‑transparent black
  overlay is drawn behind the icon while the screensaver is active.

* ``ScreensaverManager`` maintains the currently selected screensaver
  name and a single ``BouncingItem`` instance.  It exposes ``set`` to
  change the active screensaver type, ``activate``/``deactivate`` to
  control when the saver runs, ``is_active`` to query its state and
  ``update``/``draw`` to advance and render the animation.

The default idle timeout can be imported as ``DEFAULT_IDLE_SECONDS`` and
adjusted as desired.  All drawing is performed with pygame.  To use the
screensaver in your own application you should:

1. Instantiate a ``ScreensaverManager`` with an image loading function.
2. On each frame, update an idle timer based on user activity.
3. When the timer exceeds ``DEFAULT_IDLE_SECONDS`` and the selected
   screensaver is not ``"None"``, call ``activate`` with your items
   dictionary.
4. Call ``update`` each frame with the elapsed time and the screen
   rectangle.
5. After drawing your UI, call ``draw`` to overlay the screensaver.
"""

import random
import pygame

# After this many seconds of inactivity the screensaver will activate.
DEFAULT_IDLE_SECONDS = 30

# Size of the item icon displayed when bouncing.  Images will be scaled
# proportionally to fit within this box.
ICON_SIZE = (100, 100)


class BouncingItem:
    """Animate a single image bouncing within a rectangular area."""

    def __init__(self, load_image_fn):
        # Function used to load images.  Should accept a path and optional
        # ``size`` and ``colour`` arguments.  This mirrors
        # ``load_image_or_placeholder`` in the main program.
        self.load_image = load_image_fn
        # Whether the saver is currently active.
        self.active: bool = False
        # Loaded pygame.Surface for the icon.  May be None if no images were
        # available.
        self.img: pygame.Surface | None = None
        # Position of the top‑left corner of the icon as a Vector2.
        self.pos = pygame.Vector2(20.0, 20.0)
        # Velocity in pixels per second.
        self.vel = pygame.Vector2(180.0, 140.0)

    def activate(self, items: dict) -> None:
        """Select a random item image from the supplied catalogue and start bouncing.

        ``items`` should be a dictionary mapping SKU strings to dictionaries
        containing at least an ``"image"`` key.  Images are loaded using
        ``self.load_image``.  If no valid images are found the saver will
        still activate but draw only the translucent overlay.
        """
        # Collect all available image paths from the items dict.
        paths: list[str] = []
        for value in items.values():
            path = value.get("image")
            if path:
                paths.append(path)
        # Randomly pick one image, handling the case of an empty list.
        self.img = None
        if paths:
            selected = random.choice(paths)
            # Try to load with size and tint parameters; fall back to a simple
            # call if the loader does not support them.
            try:
                self.img = self.load_image(selected, size=ICON_SIZE, colour=(160, 160, 160))
            except TypeError:
                self.img = self.load_image(selected)
        # Reset position and velocity.
        self.pos = pygame.Vector2(20.0, 20.0)
        self.vel = pygame.Vector2(180.0, 140.0)
        # Mark as active.
        self.active = True

    def deactivate(self) -> None:
        """Stop the animation and hide the bouncing icon."""
        self.active = False

    def is_active(self) -> bool:
        return self.active

    def update(self, dt: float, bounds: pygame.Rect) -> None:
        """Move the icon and bounce off the edges of ``bounds``.

        ``dt`` should be the elapsed time in seconds since the last call.
        ``bounds`` defines the rectangular area within which the icon can move.
        """
        if not self.active:
            return
        # Update position based on velocity and time delta.
        self.pos += self.vel * dt
        w, h = ICON_SIZE
        # Bounce off left/right edges.
        if self.pos.x <= bounds.left:
            self.pos.x = bounds.left
            self.vel.x *= -1
        if self.pos.x + w >= bounds.right:
            self.pos.x = bounds.right - w
            self.vel.x *= -1
        # Bounce off top/bottom edges.
        if self.pos.y <= bounds.top:
            self.pos.y = bounds.top
            self.vel.y *= -1
        if self.pos.y + h >= bounds.bottom:
            self.pos.y = bounds.bottom - h
            self.vel.y *= -1

    def draw(self, screen: pygame.Surface) -> None:
        """Render the semi‑transparent overlay and the bouncing icon."""
        if not self.active:
            return
        # Draw a dark translucent overlay to dim the UI behind the screensaver.
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        # Draw the icon if one was successfully loaded.
        if self.img:
            screen.blit(self.img, (int(self.pos.x), int(self.pos.y)))


class ScreensaverManager:
    """Manage the selection and lifecycle of a screensaver animation."""

    def __init__(self, load_image_fn):
        # The name of the currently selected screensaver (e.g. "None", "Bouncing Item").
        self.name: str = "None"
        # A single BouncingItem instance used by all saver types.  Currently
        # only one saver (bouncing item) is implemented but this structure
        # allows easy expansion in the future.
        self._bouncer = BouncingItem(load_image_fn)

    def set(self, name: str) -> None:
        """Change the active screensaver selection.

        Passing ``None`` or an empty string will reset the selection to
        ``"None"``.  Selecting ``"None"`` will immediately deactivate
        any running screensaver.
        """
        self.name = (name or "None").strip()
        if self.name.lower() == "none":
            self._bouncer.deactivate()

    def activate(self, items: dict) -> None:
        """Start the selected screensaver using the provided item catalogue."""
        if self.name.lower() == "none":
            return
        # Only one saver type currently exists.  In future this could
        # dispatch based on ``self.name``.
        self._bouncer.activate(items)

    def deactivate(self) -> None:
        """Force the screensaver to stop regardless of selection."""
        self._bouncer.deactivate()

    def is_active(self) -> bool:
        return self._bouncer.is_active()

    def update(self, dt: float, bounds: pygame.Rect) -> None:
        """Update the animation if active."""
        self._bouncer.update(dt, bounds)

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the screensaver overlay and bouncing icon on the provided surface."""
        self._bouncer.draw(screen)